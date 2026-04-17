"""
Bank PDF parsing module.

This module handles the extraction of tabular financial data from bank statement
PDFs. It utilizes pdfplumber to read the document structure, parse rows of
transactions, and standardize them into Transaction objects.

Supports: ICICI, HDFC, SBI bank statement formats.
"""

import logging
import os
import re
import pdfplumber
from dateutil import parser as date_parser
from pocket_cfo_parser.models.transaction import Transaction

logger = logging.getLogger(__name__)


def _safe_amount(value: str) -> float:
    """Safely converts string amounts to float, handling commas and spaces."""
    if not value or not value.strip():
        return 0.0
    try:
        cleaned = value.replace(',', '').replace(' ', '').strip()
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def _looks_like_date(value: str) -> bool:
    if not value:
        return False
    value = value.strip()
    return bool(re.match(r"^\d{1,2}[-./\s][A-Za-z]{3}[-./\s]\d{2,4}$", value) or re.match(r"^\d{1,2}[-./]\d{1,2}[-./]\d{2,4}$", value))


def _parse_date(date_value: str):
    try:
        return date_parser.parse(date_value, dayfirst=True)
    except Exception:
        return None


def _guess_type_from_text(text: str) -> str:
    raw = (text or "").lower()
    credit_signals = ["credit", "credited", "deposit", "salary", "refund", "cashback", "cradj", "imps in", "neft in", "upi in"]
    debit_signals = ["debit", "debited", "withdraw", "purchase", "atm", "emi", "bill", "upi/", "imps", "neft", "dr"]
    if any(token in raw for token in credit_signals):
        return "credit"
    if any(token in raw for token in debit_signals):
        return "debit"
    return "debit"


def _parse_transaction_from_line(date_str: str, text_line: str) -> Transaction | None:
    # Try to capture Indian statement amounts near the line end.
    amount_tokens = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2}", text_line)
    if len(amount_tokens) < 2:
        return None

    # Most statements place transaction amount before running balance.
    txn_amount = _safe_amount(amount_tokens[-2])
    if txn_amount <= 0:
        return None

    txn_date = _parse_date(date_str)
    if not txn_date:
        return None

    txn_type = _guess_type_from_text(text_line)
    party = _extract_party_from_remarks(text_line)

    return Transaction(
        amount=txn_amount,
        type=txn_type,  # type: ignore
        party=party,
        date=txn_date,
        source="pdf",
        raw_text=text_line,
        confidence=0.78
    )


def _extract_party_from_remarks(remarks: str) -> str:
    """
    Extracts merchant/party name from transaction remarks.
    Handles UPI patterns like:
    - UPI/SIT Contee/gpay-112591429/Payment fr/AXIS BANK
    - UPI/PRAVEENA R/Q757364713@/bl/Payment fr/YES BANK
    - UPI/M S Prakas/poytm.s1qnqt@/Payment fr/YES BANK
    """
    if not remarks:
        return "Unknown"
    
    # Extract name before "@" or "/" patterns
    patterns = [
        r'UPI/([A-Z][A-Za-z\s]+?)(?:@|/)',  # UPI/NAME SURNAME@
        r'(?:UPI|NEFT|IMPS)[/:-]\s*([^/]+?)(?:/|@)',  # After NEFT/IMPS/UPI
        r'\(by:\s*([^)]+)\)',  # (by: Name)
        r'(?:fr|from)\s+([A-Za-z\s]+?)(?:\.|$)',  # from NAME
    ]
    
    for pattern in patterns:
        match = re.search(pattern, remarks, re.IGNORECASE)
        if match:
            party = match.group(1).strip().title()
            # Filter out generic terms
            if party.lower() not in ['upi', 'bank', 'payment', 'from', 'to']:
                return party
    
    # Fallback: Extract first meaningful words
    words = remarks.split()
    if len(words) > 0:
        return ' '.join(words[:2]).title()
    
    return "Unknown"


def _detect_bank_name(first_page_text: str) -> str:
    """Detects which bank the PDF belongs to."""
    if "ICICI" in first_page_text:
        return "ICICI"
    elif "HDFC" in first_page_text:
        return "HDFC"
    elif "State Bank of India" in first_page_text or "SBI" in first_page_text:
        return "SBI"
    return "Unknown"


def _find_table_with_headers(page) -> tuple[list, dict] | None:
    """
    Extracts table and returns (table_data, column_mapping).
    Identifies column positions by header names.
    Returns None if no valid table found.
    """
    table = page.extract_table()
    if not table or len(table) < 2:
        return None
    
    # First row should be headers
    header_row = [str(cell).strip().lower() if cell else "" for cell in table[0]]
    
    # Map expected headers to column index
    column_map = {}
    for idx, header in enumerate(header_row):
        if any(x in header for x in ['date', 'transaction date']):
            column_map['date'] = idx
        elif any(x in header for x in ['remarks', 'description', 'transaction remarks']):
            column_map['remarks'] = idx
        elif any(x in header for x in ['withdrawal', 'debit', 'dr']):
            column_map['withdrawal'] = idx
        elif any(x in header for x in ['deposit', 'credit', 'cr']):
            column_map['deposit'] = idx
    
    # Validate we got the essential columns
    if 'date' not in column_map or 'remarks' not in column_map:
        logger.warning(f"Table headers not recognized. Found: {header_row}")
        return None
    
    # If withdrawal/deposit not found, assume last two columns
    if 'withdrawal' not in column_map or 'deposit' not in column_map:
        if len(header_row) >= 3:
            column_map['withdrawal'] = len(header_row) - 2
            column_map['deposit'] = len(header_row) - 1
    
    return table[1:], column_map  # Skip header row


def _find_table_with_headers_from_rows(table: list[list]) -> tuple[list, dict] | None:
    if not table or len(table) < 2:
        return None

    header_row = [str(cell).strip().lower() if cell else "" for cell in table[0]]
    column_map = {}
    for idx, header in enumerate(header_row):
        if any(x in header for x in ['date', 'transaction date', 'value date']):
            if 'date' not in column_map:
                column_map['date'] = idx
            else:
                column_map['value_date'] = idx
        elif any(x in header for x in ['remarks', 'description', 'transaction remarks', 'narration', 'particulars']):
            column_map['remarks'] = idx
        elif any(x in header for x in ['withdrawal', 'debit', 'dr']):
            column_map['withdrawal'] = idx
        elif any(x in header for x in ['deposit', 'credit', 'cr']):
            column_map['deposit'] = idx
        elif 'balance' in header:
            column_map['balance'] = idx

    if 'date' not in column_map or 'remarks' not in column_map:
        return None
    return table[1:], column_map


def _parse_table_rows_generic(table_rows: list[list], column_map: dict) -> list[Transaction]:
    parsed: list[Transaction] = []
    for row in table_rows:
        if not row:
            continue
        safe = [str(cell).strip() if cell is not None else "" for cell in row]
        date_str = safe[column_map["date"]] if column_map.get("date") is not None and len(safe) > column_map["date"] else ""
        if not _looks_like_date(date_str):
            # Some statements keep date in value date column.
            v_idx = column_map.get("value_date")
            if v_idx is not None and len(safe) > v_idx and _looks_like_date(safe[v_idx]):
                date_str = safe[v_idx]
            else:
                continue

        remarks_idx = column_map["remarks"]
        remarks = safe[remarks_idx] if len(safe) > remarks_idx else ""
        if not remarks:
            remarks = "Bank Transaction"

        withdrawal = _safe_amount(safe[column_map["withdrawal"]]) if column_map.get("withdrawal") is not None and len(safe) > column_map["withdrawal"] else 0.0
        deposit = _safe_amount(safe[column_map["deposit"]]) if column_map.get("deposit") is not None and len(safe) > column_map["deposit"] else 0.0

        txn_amount = max(withdrawal, deposit)
        if txn_amount <= 0:
            continue

        txn_date = _parse_date(date_str)
        if not txn_date:
            continue

        txn_type = "credit" if deposit > withdrawal else "debit"
        party = _extract_party_from_remarks(remarks)
        raw_text = " | ".join([cell for cell in safe if cell])

        parsed.append(Transaction(
            amount=txn_amount,
            type=txn_type,  # type: ignore
            party=party,
            date=txn_date,
            source="pdf",
            raw_text=raw_text,
            confidence=0.86
        ))
    return parsed


def _parse_text_fallback(full_text: str) -> list[Transaction]:
    transactions: list[Transaction] = []
    lines = [line.strip() for line in full_text.splitlines() if line and line.strip()]
    current_date = ""
    current_line = ""

    for line in lines:
        # Skip non-transaction headers
        lower = line.lower()
        if any(token in lower for token in ["account statement", "branch address", "nominee", "currency", "account no", "transaction date", "value date"]):
            continue

        date_match = re.match(r"^(\d{1,2}[-./\s][A-Za-z]{3}[-./\s]\d{2,4}|\d{1,2}[-./]\d{1,2}[-./]\d{2,4})\s+(.*)$", line)
        if date_match:
            # Flush previous candidate
            if current_date and current_line:
                txn = _parse_transaction_from_line(current_date, current_line)
                if txn:
                    transactions.append(txn)
            current_date = date_match.group(1)
            current_line = date_match.group(2)
        elif current_date:
            current_line = f"{current_line} {line}".strip()

    if current_date and current_line:
        txn = _parse_transaction_from_line(current_date, current_line)
        if txn:
            transactions.append(txn)

    return transactions


def _parse_icici_text(text: str) -> list[Transaction]:
    """
    Parses ICICI bank statement from extracted text.
    Handles multi-line transaction entries.
    """
    transactions = []
    
    # Split by transaction rows (numbered 1, 2, 3, etc.)
    # Pattern: NUMBER DATE REST_OF_TEXT
    lines = text.split('\n')
    
    current_transaction = None
    current_remarks = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try to match start of new transaction: "NUM DATE"
        # Date format: DD.MM.YYYY
        match = re.match(r'^(\d{1,2})\s+(\d{1,2}\.\d{2}\.\d{4})\s+(.*)$', line)
        
        if match and current_transaction is None:
            # Starting a new transaction
            txn_num = match.group(1)
            date_str = match.group(2)
            first_line = match.group(3)
            
            current_transaction = {
                'date': date_str,
                'remarks': first_line
            }
            current_remarks = [first_line]
        
        elif match and current_transaction is not None:
            # Previous transaction is complete, save it
            try:
                txn = _create_transaction_from_icici(current_transaction, '\n'.join(current_remarks))
                if txn:
                    transactions.append(txn)
            except Exception as e:
                logger.warning(f"Failed to parse transaction: {e}")
            
            # Start new transaction
            txn_num = match.group(1)
            date_str = match.group(2)
            first_line = match.group(3)
            
            current_transaction = {
                'date': date_str,
                'remarks': first_line
            }
            current_remarks = [first_line]
        
        elif current_transaction is not None:
            # Continuation of current transaction remarks
            current_remarks.append(line)
    
    # Don't forget the last transaction
    if current_transaction is not None:
        try:
            txn = _create_transaction_from_icici(current_transaction, '\n'.join(current_remarks))
            if txn:
                transactions.append(txn)
        except Exception as e:
            logger.warning(f"Failed to parse last transaction: {e}")
    
    return transactions


def _create_transaction_from_icici(txn_data: dict, full_remarks: str) -> Transaction | None:
    """
    Creates a Transaction from parsed ICICI transaction data.
    Extracts amount from the full remarks line (last numbers before balance).
    """
    try:
        # Parse date
        date_str = txn_data['date']
        txn_date = date_parser.parse(date_str, dayfirst=True)
        
        # Extract amount from full remarks
        # Amount appears before the balance (last number in the line)
        # Pattern: find numbers like "10.00", "1242.00", etc.
        amounts = re.findall(r'(\d+\.?\d*)', full_remarks)
        
        if not amounts:
            return None
        
        # The last amount is usually the balance, second-to-last is the transaction amount
        # But we need to be careful - transaction amounts are smaller than balances
        # Let's take the first standalone amount that looks like a transaction
        amount = None
        for amt_str in amounts:
            amt = _safe_amount(amt_str)
            if 0 < amt < 1000000:  # Reasonable transaction range
                amount = amt
                break
        
        if not amount:
            return None
        
        # Determine if debit or credit (all visible transactions are debits/withdrawals)
        # In bank statements, withdrawn amounts are shown in one column
        txn_type = "debit"
        
        # Extract party name
        party = _extract_party_from_remarks(full_remarks)
        
        # Create transaction
        transaction = Transaction(
            amount=amount,
            type=txn_type,  # type: ignore
            party=party,
            date=txn_date,
            source="pdf",
            raw_text=full_remarks,
            confidence=0.85
        )
        
        logger.debug(f"Parsed ICICI: ₹{amount} to {party} on {txn_date.date()}")
        return transaction
    
    except Exception as e:
        logger.warning(f"Failed to create transaction: {e}")
        return None


def parse_pdf(filepath: str) -> list[Transaction]:
    """
    Parses a bank statement PDF and returns a list of Transaction objects.
    Handles ICICI, HDFC, and SBI formats automatically.
    
    For PDFs with complex layouts, falls back to text extraction.
    
    Args:
        filepath: Path to the bank statement PDF
        
    Returns:
        List of parsed Transaction objects
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)

    transactions: list[Transaction] = []
    try:
        with pdfplumber.open(filepath) as pdf:
            if not pdf.pages:
                logger.warning(f"PDF {filepath} has no pages")
                return transactions

            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"

                # First pass: extract structured tables
                for table in page.extract_tables() or []:
                    table_result = _find_table_with_headers_from_rows(table)
                    if not table_result:
                        continue
                    rows, col_map = table_result
                    transactions.extend(_parse_table_rows_generic(rows, col_map))

            bank_name = _detect_bank_name(full_text)
            logger.info(f"Detected bank: {bank_name} — parsing {len(pdf.pages)} page(s)")

            # Second pass fallback when table parsing is weak.
            if len(transactions) < 3:
                logger.info("Table extraction yielded too few rows; using text fallback parser")
                transactions.extend(_parse_text_fallback(full_text))

            # Last resort: legacy ICICI parser for odd layouts.
            if len(transactions) < 3:
                transactions.extend(_parse_icici_text(full_text))

    except Exception as e:
        logger.error(f"Failed to parse PDF {filepath}: {type(e).__name__}: {e}")
        return []

    # Deduplicate parser output by deterministic transaction hash.
    deduped = list({txn.id: txn for txn in transactions}.values())
    logger.info(f"PDF parse complete: extracted {len(deduped)} transactions from {filepath}")
    return deduped

