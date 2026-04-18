from __future__ import annotations

import re
from datetime import datetime

import pdfplumber
from dateutil import parser as date_parser


def _extract_text(filepath: str) -> str:
    with pdfplumber.open(filepath) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def _safe_amount(raw: str | None) -> float:
    if not raw:
        return 0.0
    cleaned = raw.replace(",", "").replace("INR", "").replace("Rs.", "").replace("₹", "").strip()
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if not cleaned:
        return 0.0
    try:
        return abs(float(cleaned))
    except ValueError:
        return 0.0


def _extract_invoice_number(text: str) -> str | None:
    patterns = [
        r"(?i)invoice\s*(?:no|number|#)\s*[:\-]?\s*([A-Z0-9\-/]{3,})",
        r"(?i)bill\s*(?:no|number|#)\s*[:\-]?\s*([A-Z0-9\-/]{3,})",
        r"(?i)reference\s*(?:no|number|#)\s*[:\-]?\s*([A-Z0-9\-/]{3,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_date(text: str) -> str | None:
    patterns = [
        r"(?i)(?:invoice\s*date|date\s*of\s*issue|bill\s*date|date)\s*[:\-]?\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})",
        r"(?i)(?:invoice\s*date|date\s*of\s*issue|bill\s*date|date)\s*[:\-]?\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                parsed = date_parser.parse(match.group(1), dayfirst=True)
                return parsed.isoformat()
            except Exception:
                continue

    fallback = re.search(r"([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})", text)
    if fallback:
        try:
            parsed = date_parser.parse(fallback.group(1), dayfirst=True)
            return parsed.isoformat()
        except Exception:
            return None
    return None


def _extract_total_amount(text: str) -> float:
    patterns = [
        r"(?i)(?:grand\s*total|invoice\s*value|amount\s*due|net\s*amount\s*payable|total\s*payable|total\s*amount)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        r"(?i)(?:grand\s*total|invoice\s*value|amount\s*due|net\s*amount\s*payable|total\s*payable|total\s*amount)\s*[:\-]?\s*₹\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = _safe_amount(match.group(1))
            if value > 0:
                return value

    candidates = re.findall(r"([0-9,]+\.[0-9]{2})", text)
    amounts = sorted((_safe_amount(c) for c in candidates if _safe_amount(c) > 0), reverse=True)
    return amounts[0] if amounts else 0.0


def _extract_gstin(text: str) -> str | None:
    match = re.search(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", text)
    return match.group(0) if match else None


def _extract_tax_amount(text: str) -> float:
    patterns = [
        r"(?i)(?:total\s*tax|tax\s*amount|gst\s*amount|cgst\s*\+\s*sgst\s*\+\s*igst)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = _safe_amount(match.group(1))
            if value > 0:
                return value

    component_patterns = [r"(?i)cgst\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", r"(?i)sgst\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", r"(?i)igst\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)"]
    total = 0.0
    for pattern in component_patterns:
        for match in re.finditer(pattern, text):
            total += _safe_amount(match.group(1))
    return round(total, 2)


def _extract_vendor_name(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line and line.strip()]
    skip_tokens = (
        "invoice",
        "bill",
        "gst",
        "tax",
        "date",
        "amount",
        "total",
        "phone",
        "email",
        "address",
        "hsn",
        "sac",
        "bank",
    )
    for line in lines[:25]:
        lower = line.lower()
        if any(token in lower for token in skip_tokens):
            continue
        if len(line) < 3:
            continue
        if re.search(r"[A-Za-z]", line):
            return line[:120]
    return "Unknown"


def parse_invoice_pdf(filepath: str) -> dict:
    text = _extract_text(filepath)
    invoice_number = _extract_invoice_number(text)
    invoice_date = _extract_date(text) or datetime.now().isoformat()
    total_amount = _extract_total_amount(text)
    gstin = _extract_gstin(text)
    tax_amount = _extract_tax_amount(text)
    vendor_name = _extract_vendor_name(text)

    confidence_components = [
        0.2 if invoice_number else 0.0,
        0.2 if invoice_date else 0.0,
        0.3 if total_amount > 0 else 0.0,
        0.2 if vendor_name != "Unknown" else 0.0,
        0.1 if gstin else 0.0,
    ]
    confidence = round(sum(confidence_components), 2)

    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "vendor_name": vendor_name,
        "total_amount": total_amount,
        "gstin": gstin,
        "tax_amount": tax_amount,
        "confidence": confidence,
        "raw_text": text[:12000],
    }
