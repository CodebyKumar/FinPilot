from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from dateutil import parser as date_parser

from finpilot.models.transaction import Transaction
from finpilot.services.parsers.pdf_parser import parse_pdf


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_amount(value: Any) -> float:
    text = _safe_text(value).replace(",", "").replace("₹", "").replace("INR", "")
    if not text:
        return 0.0

    sign = -1.0 if ("(" in text and ")" in text) or text.startswith("-") else 1.0
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    if not cleaned:
        return 0.0
    try:
        return sign * float(cleaned)
    except ValueError:
        return 0.0


def _parse_date(value: Any):
    text = _safe_text(value)
    if not text:
        return None
    try:
        return date_parser.parse(text, dayfirst=True, fuzzy=True)
    except Exception:
        return None


def _pick_first_key(row: dict[str, Any], candidate_keys: tuple[str, ...]) -> str | None:
    key_map = {str(k).strip().lower(): k for k in row.keys()}
    for candidate in candidate_keys:
        for normalized, original in key_map.items():
            if candidate in normalized:
                return original
    return None


def _parse_csv_statement(file_path: str) -> list[Transaction]:
    rows: list[dict[str, Any]] = []
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                rows = [row for row in reader if row]
            break
        except Exception:
            continue

    if not rows:
        return []

    txns: list[Transaction] = []
    for row in rows:
        date_key = _pick_first_key(row, ("date", "value date", "txn date", "transaction date"))
        desc_key = _pick_first_key(row, ("description", "narration", "particular", "remarks", "details"))
        debit_key = _pick_first_key(row, ("debit", "withdraw", "dr"))
        credit_key = _pick_first_key(row, ("credit", "deposit", "cr"))
        amount_key = _pick_first_key(row, ("amount", "txn amount", "transaction amount"))
        type_key = _pick_first_key(row, ("dr/cr", "type"))

        date_val = _parse_date(row.get(date_key) if date_key else None)
        if date_val is None:
            continue

        description = _safe_text(row.get(desc_key) if desc_key else "") or "Bank transaction"
        debit_amount = _safe_amount(row.get(debit_key) if debit_key else None)
        credit_amount = _safe_amount(row.get(credit_key) if credit_key else None)
        amount_value = _safe_amount(row.get(amount_key) if amount_key else None)
        type_value = _safe_text(row.get(type_key) if type_key else "").lower()

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
            if "cr" in type_value or "credit" in type_value:
                txn_type = "credit"
            elif "dr" in type_value or "debit" in type_value:
                txn_type = "debit"
            elif amount_value < 0:
                txn_type = "debit"
            else:
                txn_type = "debit"

        if amount <= 0:
            continue

        txns.append(
            Transaction(
                amount=round(amount, 2),
                type=txn_type,
                party="Unknown",
                date=date_val,
                source="pdf",
                raw_text=description[:4000],
                confidence=0.75,
            )
        )

    return txns


def parse_statement_file(file_path: str) -> list[Transaction]:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".csv":
        return _parse_csv_statement(file_path)
    return parse_pdf(file_path)
