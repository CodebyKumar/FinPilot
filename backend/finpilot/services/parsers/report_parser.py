from __future__ import annotations

import re

import pdfplumber


COMMON_FORM_FIELDS = [
    "First Name",
    "Last Name",
    "PAN",
    "Aadhaar",
    "Date of Birth",
    "Business Name",
    "Entity Type",
    "GSTIN",
    "Assessment Year",
]


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _is_placeholder(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    if re.fullmatch(r"[_\-.\s]+", stripped):
        return True
    return False


def _extract_text(filepath: str) -> str:
    with pdfplumber.open(filepath) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def extract_fields_from_template_text(template_text: str) -> list[dict]:
    lines = [_normalize_spaces(line) for line in template_text.splitlines() if line and _normalize_spaces(line)]
    fields: list[dict] = []
    seen: set[tuple[str, str]] = set()
    fallback_idx = 1

    id_pattern_alpha = re.compile(r"^([A-Z]{1,4}\d{1,4})[\).:\-\s]+(.+)$")
    id_pattern_num = re.compile(r"^(\d{1,3})[\).:\-\s]+(.+)$")

    for line in lines:
        field_id = ""
        field_name = ""
        value = None

        match_alpha = id_pattern_alpha.match(line)
        if match_alpha:
            field_id = match_alpha.group(1).strip()
            field_name = _normalize_spaces(match_alpha.group(2))
        else:
            match_num = id_pattern_num.match(line)
            if match_num:
                field_id = f"A{match_num.group(1).strip()}"
                field_name = _normalize_spaces(match_num.group(2))
            elif ":" in line:
                left, right = line.split(":", 1)
                left = _normalize_spaces(left)
                right = _normalize_spaces(right)
                if left and len(left) <= 120 and re.search(r"[A-Za-z]", left):
                    field_id = f"A{fallback_idx}"
                    fallback_idx += 1
                    field_name = left
                    value = None if _is_placeholder(right) else right

        if not field_name:
            lower = line.lower()
            if any(key.lower() in lower for key in COMMON_FORM_FIELDS):
                field_id = f"A{fallback_idx}"
                fallback_idx += 1
                field_name = line

        if not field_name:
            continue

        if len(field_name) > 200:
            field_name = field_name[:200]

        dedupe_key = (field_id, field_name.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        fields.append(
            {
                "field_id": field_id or f"A{fallback_idx}",
                "field_name": field_name,
                "value": value,
                "status": "filled" if value not in (None, "") else "pending",
            }
        )

    if not fields:
        for idx, name in enumerate(COMMON_FORM_FIELDS, start=1):
            fields.append({"field_id": f"A{idx}", "field_name": name, "value": None, "status": "pending"})

    return fields


def extract_fields_from_report_pdf(filepath: str) -> dict:
    template_text = _extract_text(filepath)
    fields = extract_fields_from_template_text(template_text)
    return {"fields": fields, "template_text": template_text[:20000]}


def extract_filled_fields_from_pdf(filepath: str) -> list[dict]:
    text = _extract_text(filepath)
    lines = [_normalize_spaces(line) for line in text.splitlines() if line and _normalize_spaces(line)]
    fields: list[dict] = []
    idx = 1

    for line in lines:
        if ":" not in line:
            continue
        left, right = line.split(":", 1)
        left = _normalize_spaces(left)
        right = _normalize_spaces(right)
        if not left or len(left) > 120:
            continue
        if _is_placeholder(right):
            value = None
            status = "missing"
        else:
            value = right
            status = "filled"

        fields.append({"field_id": f"A{idx}", "field_name": left, "value": value, "status": status})
        idx += 1

    if fields:
        return fields

    return extract_fields_from_template_text(text)
