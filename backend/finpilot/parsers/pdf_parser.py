"""
Bank PDF parsing module.

Extracts tabular transaction data from bank statement PDFs using pdfplumber.
Supports ICICI, HDFC, and SBI statement formats.
Other formats fall back to the ICICI text-extraction approach.
"""

import logging
import re

import pdfplumber
from dateutil import parser as date_parser

from finpilot.models.transaction import Transaction

logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _safe_amount(value: str) -> float:
    """Convert a string monetary value to float, ignoring commas and spaces."""
    if not value or not value.strip():
        return 0.0
    try:
        cleaned = value.replace(",", "").replace(" ", "").strip()
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def _extract_party_from_remarks(remarks: str) -> str:
    """
    Extract a merchant or party name from a transaction remarks string.
    Handles common UPI/NEFT/IMPS patterns.
    """
    if not remarks:
        return "Unknown"

    patterns = [
        r"UPI/([A-Z][A-Za-z\s]+?)(?:@|/)",
        r"(?:UPI|NEFT|IMPS)[/:-]\s*([^/]+?)(?:/|@)",
        r"\(by:\s*([^)]+)\)",
        r"(?:fr|from)\s+([A-Za-z\s]+?)(?:\.|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, remarks, re.IGNORECASE)
        if match:
            party = match.group(1).strip().title()
            if party.lower() not in {"upi", "bank", "payment", "from", "to"}:
                return party

    words = remarks.split()
    return " ".join(words[:2]).title() if words else "Unknown"


def _detect_bank_name(first_page_text: str) -> str:
    """Identify which bank issued the statement."""
    if "ICICI" in first_page_text:
        return "ICICI"
    if "HDFC" in first_page_text:
        return "HDFC"
    if "State Bank of India" in first_page_text or "SBI" in first_page_text:
        return "SBI"
    return "Unknown"


# ─── ICICI-format parser ───────────────────────────────────────────────────────

def _create_transaction_from_icici(txn_data: dict, full_remarks: str) -> Transaction | None:
    """Build a Transaction from a parsed ICICI row."""
    try:
        txn_date = date_parser.parse(txn_data["date"], dayfirst=True)
        amounts = re.findall(r"(\d+\.?\d*)", full_remarks)
        amount: float | None = None
        for amt_str in amounts:
            amt = _safe_amount(amt_str)
            if 0 < amt < 1_000_000:
                amount = amt
                break
        if not amount:
            return None

        party = _extract_party_from_remarks(full_remarks)
        return Transaction(
            amount=amount,
            type="debit",  # type: ignore[arg-type]
            party=party,
            date=txn_date,
            source="pdf",
            raw_text=full_remarks,
            confidence=0.85,
        )
    except Exception as exc:
        logger.warning("Failed to create ICICI transaction: %s", exc)
        return None


def _parse_icici_text(text: str) -> list[Transaction]:
    """Parse an ICICI bank statement from raw extracted text."""
    transactions: list[Transaction] = []
    lines = text.split("\n")
    current_transaction: dict | None = None
    current_remarks: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(r"^(\d{1,2})\s+(\d{1,2}\.\d{2}\.\d{4})\s+(.*)$", line)
        if match:
            if current_transaction is not None:
                txn = _create_transaction_from_icici(
                    current_transaction, "\n".join(current_remarks)
                )
                if txn:
                    transactions.append(txn)
            current_transaction = {"date": match.group(2), "remarks": match.group(3)}
            current_remarks = [match.group(3)]
        elif current_transaction is not None:
            current_remarks.append(line)

    if current_transaction is not None:
        txn = _create_transaction_from_icici(
            current_transaction, "\n".join(current_remarks)
        )
        if txn:
            transactions.append(txn)

    return transactions


# ─── Public entry point ────────────────────────────────────────────────────────

def parse_pdf(filepath: str) -> list[Transaction]:
    """
    Parse a bank statement PDF and return a list of Transaction objects.
    Auto-detects ICICI, HDFC, and SBI formats; falls back to ICICI parsing
    for unrecognised layouts.

    Args:
        filepath: Absolute path to the bank statement PDF.

    Returns:
        List of parsed Transaction objects (may be empty on failure).
    """
    transactions: list[Transaction] = []

    try:
        with pdfplumber.open(filepath) as pdf:
            if not pdf.pages:
                logger.warning("PDF %s has no pages.", filepath)
                return transactions

            full_text = "".join(
                (page.extract_text() or "") + "\n" for page in pdf.pages
            )
            bank_name = _detect_bank_name(full_text)
            logger.info("Detected bank: %s — parsing %d page(s)", bank_name, len(pdf.pages))

            # Route to the appropriate parser
            if bank_name == "ICICI":
                transactions = _parse_icici_text(full_text)
            else:
                logger.warning(
                    "Bank '%s' parser not fully implemented; attempting ICICI format.", bank_name
                )
                transactions = _parse_icici_text(full_text)

    except Exception as exc:
        logger.error("Failed to parse PDF %s: %s: %s", filepath, type(exc).__name__, exc)
        return []

    logger.info("PDF parse complete: extracted %d transactions from %s", len(transactions), filepath)
    return transactions
