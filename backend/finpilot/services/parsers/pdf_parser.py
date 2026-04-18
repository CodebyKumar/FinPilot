import logging
import re

import pdfplumber
from dateutil import parser as date_parser

from finpilot.models.transaction import Transaction

logger = logging.getLogger(__name__)


def _safe_text(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _safe_amount(value: str | None) -> float:
    if not value:
        return 0.0
    text = _safe_text(value)
    text = text.replace(",", "").replace("₹", "").replace("INR", "")
    sign = -1.0 if ("(" in text and ")" in text) or "-" in text else 1.0
    text = re.sub(r"[^0-9.]", "", text)
    if not text:
        return 0.0
    try:
        return sign * float(text)
    except ValueError:
        return 0.0


def _parse_date(value: str | None):
    if not value:
        return None
    text = _safe_text(value)
    if not text:
        return None
    try:
        return date_parser.parse(text, dayfirst=True, fuzzy=True)
    except Exception:
        return None


def _extract_party(description: str) -> str:
    text = _safe_text(description)
    if not text:
        return "Unknown"

    patterns = [
        r"(?i)(?:UPI|IMPS|NEFT|RTGS)[/\-]\s*([^/@\-]+)",
        r"(?i)(?:to|from)\s+([A-Za-z][A-Za-z0-9\s.&\-]{2,60})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            party = _safe_text(match.group(1)).title()
            if party:
                return party

    words = [w for w in re.split(r"\s+", text) if w]
    if not words:
        return "Unknown"
    return " ".join(words[:3]).title()[:80]


def _find_col_idx(headers: list[str], keys: tuple[str, ...]) -> int | None:
    for idx, header in enumerate(headers):
        if any(key in header for key in keys):
            return idx
    return None


def _extract_from_tables(pdf: pdfplumber.PDF) -> list[Transaction]:
    txns: list[Transaction] = []

    for page in pdf.pages:
        tables = page.extract_tables() or []
        for table in tables:
            if not table or len(table) < 2:
                continue

            header_row = [_safe_text(c).lower() for c in table[0]]
            if not header_row:
                continue

            date_idx = _find_col_idx(header_row, ("date", "txn date", "transaction date", "value date"))
            desc_idx = _find_col_idx(header_row, ("description", "particular", "narration", "remarks", "details", "transaction"))
            debit_idx = _find_col_idx(header_row, ("debit", "withdraw", "dr"))
            credit_idx = _find_col_idx(header_row, ("credit", "deposit", "cr"))
            amount_idx = _find_col_idx(header_row, ("amount", "txn amount", "transaction amount"))
            drcr_idx = _find_col_idx(header_row, ("dr/cr", "type"))

            if date_idx is None:
                continue
            if debit_idx is None and credit_idx is None and amount_idx is None:
                continue

            for row in table[1:]:
                if not row:
                    continue
                cells = [_safe_text(c) for c in row]
                if all(not c for c in cells):
                    continue

                date_val = _parse_date(cells[date_idx] if date_idx < len(cells) else "")
                if date_val is None:
                    continue

                description = cells[desc_idx] if desc_idx is not None and desc_idx < len(cells) else ""
                debit_amount = _safe_amount(cells[debit_idx]) if debit_idx is not None and debit_idx < len(cells) else 0.0
                credit_amount = _safe_amount(cells[credit_idx]) if credit_idx is not None and credit_idx < len(cells) else 0.0
                amount_value = _safe_amount(cells[amount_idx]) if amount_idx is not None and amount_idx < len(cells) else 0.0
                drcr_value = cells[drcr_idx].lower() if drcr_idx is not None and drcr_idx < len(cells) else ""

                txn_type = "debit"
                amount = 0.0

                if debit_amount > 0 and credit_amount == 0:
                    txn_type = "debit"
                    amount = debit_amount
                elif credit_amount > 0 and debit_amount == 0:
                    txn_type = "credit"
                    amount = credit_amount
                elif amount_value != 0:
                    amount = abs(amount_value)
                    if "cr" in drcr_value or "credit" in drcr_value:
                        txn_type = "credit"
                    elif "dr" in drcr_value or "debit" in drcr_value:
                        txn_type = "debit"
                    elif amount_value < 0:
                        txn_type = "debit"
                    elif re.search(r"(?i)credit|cr", description):
                        txn_type = "credit"
                    else:
                        txn_type = "debit"

                if amount <= 0:
                    continue

                raw_text = description or "Bank transaction"
                party = _extract_party(raw_text)

                txns.append(
                    Transaction(
                        amount=round(amount, 2),
                        type=txn_type,
                        party=party,
                        date=date_val,
                        source="pdf",
                        raw_text=raw_text,
                        confidence=0.9,
                    )
                )

    return txns


def _extract_from_lines(text: str) -> list[Transaction]:
    txns: list[Transaction] = []
    lines = [_safe_text(line) for line in text.splitlines() if _safe_text(line)]
    date_pattern = re.compile(
        r"\b(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|\d{4}[\-/]\d{1,2}[\-/]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})\b"
    )
    amount_pattern = re.compile(r"[-+]?\d[\d,]*(?:\.\d{1,2})?")

    for line in lines:
        date_match = date_pattern.search(line)
        if not date_match:
            continue

        date_val = _parse_date(date_match.group(1))
        if date_val is None:
            continue

        amount_matches = amount_pattern.findall(line)
        numeric_candidates = []
        for raw in amount_matches:
            stripped = raw.strip()
            if not stripped:
                continue
            # Skip tokens likely to be day/month/year fragments
            if len(stripped.replace(",", "")) <= 2:
                continue
            numeric_candidates.append(stripped)

        if not numeric_candidates:
            continue

        raw_amount = numeric_candidates[-1]
        amount_value = _safe_amount(raw_amount)
        if amount_value == 0:
            continue

        txn_type = "debit"
        lower_line = line.lower()
        if " credit" in lower_line or " cr" in lower_line:
            txn_type = "credit"
        elif " debit" in lower_line or " dr" in lower_line:
            txn_type = "debit"
        elif raw_amount.strip().startswith("-"):
            txn_type = "debit"
        else:
            txn_type = "debit"

        clean_line = line.replace(date_match.group(1), "")
        clean_line = re.sub(r"[-+]?[0-9,]+\.[0-9]{2}", "", clean_line)
        raw_text = _safe_text(clean_line) or line
        party = _extract_party(raw_text)

        txns.append(
            Transaction(
                amount=round(abs(amount_value), 2),
                type=txn_type,
                party=party,
                date=date_val,
                source="pdf",
                raw_text=raw_text,
                confidence=0.7,
            )
        )

    return txns


def _dedupe_transactions(transactions: list[Transaction]) -> list[Transaction]:
    seen: set[str] = set()
    unique: list[Transaction] = []
    for txn in transactions:
        if txn.id in seen:
            continue
        seen.add(txn.id)
        unique.append(txn)
    return unique


def parse_pdf(filepath: str) -> list[Transaction]:
    try:
        with pdfplumber.open(filepath) as pdf:
            table_txns = _extract_from_tables(pdf)
            if table_txns:
                unique = _dedupe_transactions(table_txns)
                logger.info("PDF parse complete: extracted %d transactions from %s", len(unique), filepath)
                return unique

            full_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
            line_txns = _extract_from_lines(full_text)
            unique = _dedupe_transactions(line_txns)
            logger.info("PDF parse complete: extracted %d transactions from %s", len(unique), filepath)
            return unique
    except Exception as exc:
        logger.error("Failed to parse PDF %s: %s: %s", filepath, type(exc).__name__, exc)
        return []
