from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import os
import re
from uuid import uuid4
from typing import Any

from dateutil import parser as date_parser
from fastapi import BackgroundTasks

from finpilot import config
from finpilot.db.mongo import _get_db, get_user, save_user, save_transaction
from finpilot.api.deps import fetch_user_transactions
from finpilot.models.transaction import Transaction
from finpilot.agents.bookkeeping_agent import get_bookkeeping_summary
from finpilot.agents.gst_agent import classify_transaction
from finpilot.agents.orchestrator_agent import execute_goal
from finpilot.services.ingestion import ingest_pdf
from finpilot.services.parsers.invoice_parser import parse_invoice_pdf
from finpilot.services.parsers.report_parser import (
    extract_fields_from_template_text,
    extract_fields_from_report_pdf,
    extract_filled_fields_from_pdf,
)
from finpilot.tasks.deadline_worker import scan_deadlines_once, dispatch_queued_notifications
from finpilot.utils.profile_security import (
    decrypt_sensitive_value,
    encrypt_sensitive_value,
    mask_sensitive_value,
)


PROFILE_SECTION_DEFAULTS: dict[str, Any] = {
    "personal_info": {},
    "business_info": {},
    "income_sources": [],
    "bank_accounts": [],
    "tax_preferences": {},
}

REQUIRED_PROFILE_FIELDS = (
    "personal_info.full_name",
    "personal_info.dob",
    "personal_info.pan",
    "personal_info.phone",
    "business_info.business_name",
    "business_info.entity_type",
)

SENSITIVE_PROFILE_FIELDS = {"pan", "aadhaar"}

ASSISTANT_SCOPE_KEYWORDS = (
    "tax",
    "gst",
    "itc",
    "tds",
    "compliance",
    "bookkeeping",
    "ledger",
    "invoice",
    "profit",
    "expense",
    "cashflow",
    "report",
    "filing",
    "finance",
    "deduction",
)

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
AADHAAR_REGEX = re.compile(r"^[0-9]{12}$")
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"^[6-9][0-9]{9}$")
ASSESSMENT_YEAR_REGEX = re.compile(r"^20[0-9]{2}-[0-9]{2}$")


def _now_iso() -> str:
    return datetime.now().isoformat()


def _jobs_collection():
    return _get_db()["jobs"]


def _profiles_collection():
    return _get_db()["profiles"]


def _reports_collection():
    return _get_db()["reports"]


def _deadlines_collection():
    return _get_db()["deadlines"]


def _invoices_collection():
    return _get_db()["invoices"]


def _safe_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _parse_datetime(raw: str | None):
    if not raw:
        return datetime.now()
    try:
        return date_parser.parse(raw, dayfirst=True)
    except Exception:
        return datetime.now()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _extract_report_fields(payload: dict[str, Any]) -> list[dict[str, Any]]:
    report_name = payload.get("report_name", "Generic Report")
    file_path = payload.get("file_path")
    if file_path and os.path.exists(file_path):
        parsed = extract_fields_from_report_pdf(file_path)
        fields = parsed.get("fields", [])
        if fields:
            return _refine_report_fields_with_ai(report_name, parsed.get("template_text", ""), fields)

    template_text = payload.get("report_template_text")
    if template_text:
        fields = extract_fields_from_template_text(str(template_text))
        if fields:
            return _refine_report_fields_with_ai(report_name, str(template_text), fields)

    return _extract_fields_from_payload(payload)


def _coerce_field_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if isinstance(item, dict):
            normalized.append({
                "field_id": _safe_text(item.get("field_id") or item.get("id") or f"A{index}"),
                "field_name": _safe_text(item.get("field_name") or item.get("name") or item.get("label") or f"Field {index}"),
                "value": item.get("value"),
                "status": _safe_text(item.get("status") or ("filled" if item.get("value") not in (None, "") else "pending")),
            })
        elif isinstance(item, str):
            normalized.append({
                "field_id": f"A{index}",
                "field_name": _safe_text(item),
                "value": None,
                "status": "pending",
            })
    return normalized


def _refine_report_fields_with_ai(report_name: str, extracted_text: str, fallback_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = _safe_text(extracted_text)
    if not text:
        return _coerce_field_list(fallback_fields)

    api_key = config.OPENAI_API_KEY
    if not api_key:
        return _coerce_field_list(fallback_fields)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract Indian tax/report form fields from noisy PDF/OCR text. "
                        "Remove gibberish, repeated headers/footers, page numbers, and unrelated text. "
                        "Return ONLY valid JSON with this shape: {\"fields\": [{\"field_id\": \"A1\", \"field_name\": \"...\", \"value\": null, \"status\": \"pending|filled\"}]}. "
                        "Keep only genuine form fields that belong to the report. Prefer concise field names."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Report type: {report_name}\n"
                        f"Noisy PDF text:\n{text[:20000]}\n\n"
                        "Existing candidate fields (use as hints, but remove noise):\n"
                        f"{json.dumps(fallback_fields[:100], ensure_ascii=False)}"
                    ),
                },
            ],
        )

        content = response.choices[0].message.content or ""
        parsed = json.loads(content)
        ai_fields = _coerce_field_list(parsed.get("fields", []))
        return ai_fields if ai_fields else _coerce_field_list(fallback_fields)
    except Exception:
        return _coerce_field_list(fallback_fields)


def _prefill_report_fields_from_profile(user_id: str, fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profile_values = _profile_value_map(user_id)
    ledger_values = _ledger_value_map(user_id)
    combined_values = {**ledger_values, **profile_values}
    filled: list[dict[str, Any]] = []

    for field in fields:
        if not isinstance(field, dict):
            continue

        field_name = _safe_text(field.get("field_name") or field.get("name") or "")
        existing_value = field.get("value")
        selected_value = existing_value

        if selected_value in (None, "", "-", "—", "N/A", "NA"):
            selected_value = _match_value_for_field(field_name, combined_values)

        status = field.get("status") or "pending"
        if selected_value not in (None, ""):
            status = "filled"

        filled.append({
            "field_id": field.get("field_id") or field.get("id") or f"A{len(filled) + 1}",
            "field_name": field_name or f"Field {len(filled) + 1}",
            "value": selected_value,
            "status": status,
            "source": field.get("source") or ("profile" if selected_value not in (None, "") else "manual"),
        })

    return filled


def _match_value_for_field(field_name: str, values: dict[str, Any]):
    normalized_name = _normalize_key(field_name)
    best_value = None
    best_score = 0

    for key, value in values.items():
        if value in (None, ""):
            continue
        normalized_key = _normalize_key(key)
        if not normalized_key:
            continue

        score = 0
        if normalized_key == normalized_name:
            score = 100
        elif normalized_key in normalized_name:
            score = 75
        elif normalized_name in normalized_key:
            score = 60
        else:
            key_tokens = set(re.findall(r"[a-z0-9]+", key.lower()))
            name_tokens = set(re.findall(r"[a-z0-9]+", field_name.lower()))
            overlap = len(key_tokens & name_tokens)
            if overlap > 0:
                score = overlap * 10

        if score > best_score:
            best_score = score
            best_value = value

    return best_value if best_score >= 20 else None


def _merge_dicts(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _validate_profile_structure(payload: dict[str, Any], partial: bool) -> None:
    for key, default_value in PROFILE_SECTION_DEFAULTS.items():
        if partial and key not in payload:
            continue
        value = payload.get(key, default_value)
        if isinstance(default_value, dict) and not isinstance(value, dict):
            raise ValueError(f"{key} must be an object")
        if isinstance(default_value, list) and not isinstance(value, list):
            raise ValueError(f"{key} must be a list")


def _missing_required_profile_fields(payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field_path in REQUIRED_PROFILE_FIELDS:
        section, field_name = field_path.split(".", 1)
        section_data = payload.get(section, {})
        value = section_data.get(field_name) if isinstance(section_data, dict) else None
        if value in (None, ""):
            missing.append(field_path)
    return missing


def _encrypt_profile_doc(doc: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(doc)
    personal = result.get("personal_info")
    if isinstance(personal, dict):
        for key in SENSITIVE_PROFILE_FIELDS:
            if key in personal:
                personal[key] = encrypt_sensitive_value(personal.get(key))
    return result


def _decrypt_profile_doc(doc: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(doc)
    personal = result.get("personal_info")
    if isinstance(personal, dict):
        for key in SENSITIVE_PROFILE_FIELDS:
            if key in personal:
                personal[key] = decrypt_sensitive_value(personal.get(key))
    return result


def _mask_profile_doc(doc: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(doc)
    personal = result.get("personal_info")
    if isinstance(personal, dict):
        for key in SENSITIVE_PROFILE_FIELDS:
            if key in personal:
                decrypted = decrypt_sensitive_value(personal.get(key))
                personal[key] = mask_sensitive_value(decrypted)
    return result


def _normalize_profile_payload(payload: dict[str, Any], partial: bool) -> dict[str, Any]:
    _validate_profile_structure(payload, partial=partial)

    normalized: dict[str, Any] = {}
    for key, default_value in PROFILE_SECTION_DEFAULTS.items():
        if partial and key not in payload:
            continue
        normalized[key] = payload.get(key, deepcopy(default_value))

    normalized["updated_at"] = _now_iso()
    return _encrypt_profile_doc(normalized)


def _task_create_profile(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_required_profile_fields(payload)
    if missing:
        raise ValueError(f"Missing mandatory profile fields: {', '.join(missing)}")

    profile_doc = _normalize_profile_payload(payload, partial=False)
    profile_doc["user_id"] = user_id
    profile_doc["created_at"] = _now_iso()
    profile_doc["deleted"] = False

    decrypted_doc = _decrypt_profile_doc(profile_doc)
    personal = decrypted_doc.get("personal_info", {})
    business = decrypted_doc.get("business_info", {})

    name = personal.get("full_name") or payload.get("name") or "Unknown"
    phone = personal.get("phone") or payload.get("phone") or f"user-{user_id}"
    business_name = business.get("business_name") or payload.get("business_name") or "Unknown"
    industry = business.get("industry") or payload.get("industry") or "Unknown"
    entity_type = business.get("entity_type") or payload.get("entity_type") or "Unknown"
    annual_turnover = float(business.get("annual_turnover") or payload.get("annual_turnover") or 0.0)

    backend_user_id = save_user(
        name=name,
        phone=phone,
        business_name=business_name,
        industry=industry,
        entity_type=entity_type,
        annual_turnover=annual_turnover,
        external_user_id=user_id,
    )

    _profiles_collection().update_one(
        {"user_id": user_id},
        {"$set": profile_doc},
        upsert=True,
    )

    return {
        "profile_saved": True,
        "backend_user_id": backend_user_id,
        "user_id": user_id,
        "profile": _mask_profile_doc(profile_doc),
    }


def _task_get_profile(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    user_doc = get_user(user_id)
    profile_doc = _profiles_collection().find_one(
        {"user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0},
    )
    return {
        "user": user_doc,
        "profile": _mask_profile_doc(profile_doc or {}),
    }


def _task_update_profile(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        raise ValueError("payload is required for update_profile")

    existing = _profiles_collection().find_one({"user_id": user_id}, {"_id": 0}) or {
        "user_id": user_id,
        "created_at": _now_iso(),
        "deleted": False,
    }

    update_doc = _normalize_profile_payload(payload, partial=True)
    merged = _merge_dicts(existing, update_doc)
    merged["user_id"] = user_id
    merged["updated_at"] = _now_iso()

    _profiles_collection().update_one(
        {"user_id": user_id},
        {"$set": merged},
        upsert=True,
    )

    decrypted_merged = _decrypt_profile_doc(merged)
    business = decrypted_merged.get("business_info", {})
    personal = decrypted_merged.get("personal_info", {})

    if isinstance(business, dict):
        name = personal.get("full_name") or payload.get("name") or "Unknown"
        phone = personal.get("phone") or payload.get("phone") or f"user-{user_id}"
        business_name = business.get("business_name") or "Unknown"
        industry = business.get("industry") or "Unknown"
        entity_type = business.get("entity_type") or "Unknown"
        annual_turnover = float(business.get("annual_turnover") or 0.0)
        save_user(
            name=name,
            phone=phone,
            business_name=business_name,
            industry=industry,
            entity_type=entity_type,
            annual_turnover=annual_turnover,
            external_user_id=user_id,
        )

    return {
        "updated": True,
        "user_id": user_id,
        "profile": _mask_profile_doc(merged),
    }


def _task_delete_profile(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = _profiles_collection().update_one(
        {"user_id": user_id},
        {"$set": {"deleted": True, "deleted_at": _now_iso(), "updated_at": _now_iso()}},
        upsert=False,
    )
    return {"deleted": result.modified_count > 0, "user_id": user_id}


def _task_bookkeeping_add_entry(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    amount = float(payload.get("amount", 0.0))
    txn_type = payload.get("type", "debit")
    party = payload.get("party", "Unknown")
    source = payload.get("source", "ocr")
    raw_text = payload.get("raw_text", "manual-entry")
    date_raw = payload.get("date")
    if date_raw:
        try:
            date_val = datetime.fromisoformat(date_raw)
        except ValueError:
            date_val = datetime.now()
    else:
        date_val = datetime.now()

    txn = Transaction(
        amount=amount,
        type=txn_type,
        party=party,
        date=date_val,
        source=source,
        raw_text=raw_text,
        category=payload.get("category", "Uncategorized"),
        sub_category=payload.get("sub_category", "Uncategorized"),
        business_nature=payload.get("business_nature", "business"),
        gst_rate=float(payload.get("gst_rate", 0.0)),
        itc_eligible=bool(payload.get("itc_eligible", False)),
        hsn_sac=payload.get("hsn_sac", "UNKNOWN"),
        gst_amount=float(payload.get("gst_amount", 0.0)),
        itc_amount=float(payload.get("itc_amount", 0.0)),
        matched_rule=payload.get("matched_rule", "manual"),
        confidence=float(payload.get("confidence", 1.0)),
    )

    should_auto_classify = (
        payload.get("category") in (None, "", "Uncategorized", "uncategorized")
        and float(payload.get("gst_rate", 0.0) or 0.0) == 0.0
        and payload.get("matched_rule") in (None, "", "manual")
    )
    if should_auto_classify:
        classification = classify_transaction(txn)
        txn.category = classification.get("category", "Uncategorized")
        txn.sub_category = classification.get("sub_category", "Uncategorized")
        txn.business_nature = classification.get("business_nature", "business")
        txn.gst_rate = float(classification.get("gst_rate", 0.0))
        txn.itc_eligible = bool(classification.get("itc_eligible", False))
        txn.hsn_sac = classification.get("hsn_sac", "UNKNOWN")
        txn.gst_amount = float(classification.get("gst_amount", 0.0))
        txn.itc_amount = float(classification.get("itc_amount", 0.0))
        txn.matched_rule = classification.get("matched_rule", "auto")
        txn.confidence = max(txn.confidence, float(classification.get("confidence", 0.7)))

    save_result = save_transaction(txn, user_id)
    return {
        "saved": save_result is not None,
        "transaction": txn.to_dict(),
    }


def _task_bookkeeping_get_ledger(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    txns = fetch_user_transactions(user_id)
    return get_bookkeeping_summary(txns)


def _task_bookkeeping_update_entry(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    entry_id = payload.get("entry_id")
    updates = payload.get("updates", {})
    if not entry_id:
        return {"updated": False, "error": "entry_id is required"}

    updates["updated_at"] = _now_iso()
    result = _get_db()["transactions"].update_one({"_id": entry_id, "user_id": user_id}, {"$set": updates})
    return {"updated": result.modified_count > 0, "entry_id": entry_id}


def _task_bookkeeping_upload_statement(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    file_path = payload.get("file_path")
    if not file_path:
        return {"uploaded": False, "error": "file_path is required"}
    transactions = ingest_pdf(file_path, user_id)
    count = len(transactions)
    message = "Statement parsed successfully" if count > 0 else (
        "No transactions could be parsed from this statement. "
        "The file may be image-only/scanned, password-protected, or in an unsupported layout."
    )
    return {
        "uploaded": True,
        "parsed": count > 0,
        "count": count,
        "message": message,
        "transactions": [t.to_dict() for t in transactions],
    }


def _task_bookkeeping_upload_invoice(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    file_path = payload.get("file_path")
    extracted: dict[str, Any] = {}

    if file_path and os.path.exists(file_path):
        extracted = parse_invoice_pdf(file_path)

    final_amount = float(payload.get("amount") or extracted.get("total_amount") or 0.0)
    final_party = payload.get("party") or extracted.get("vendor_name") or "Unknown"
    final_date_raw = payload.get("date") or extracted.get("invoice_date") or _now_iso()
    final_date = _parse_datetime(final_date_raw)

    doc = {
        "invoice_id": payload.get("invoice_id") or str(uuid4()),
        "user_id": user_id,
        "file_path": file_path,
        "amount": final_amount,
        "date": final_date.isoformat(),
        "party": final_party,
        "linked_transaction_id": payload.get("linked_transaction_id"),
        "notes": payload.get("notes", ""),
        "extracted": extracted,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    linked_transaction = None
    if final_amount > 0:
        txn = Transaction(
            amount=final_amount,
            type="debit",
            party=final_party,
            date=final_date,
            source="ocr",
            raw_text=(extracted.get("raw_text") or payload.get("notes") or "Invoice expense")[:4000],
            confidence=float(extracted.get("confidence", 0.8)),
        )
        classification = classify_transaction(txn)
        txn.category = classification.get("category", "Uncategorized")
        txn.sub_category = classification.get("sub_category", "Uncategorized")
        txn.business_nature = classification.get("business_nature", "business")
        txn.gst_rate = float(classification.get("gst_rate", 0.0))
        txn.itc_eligible = bool(classification.get("itc_eligible", False))
        txn.hsn_sac = classification.get("hsn_sac", "UNKNOWN")
        txn.gst_amount = float(classification.get("gst_amount", 0.0))
        txn.itc_amount = float(classification.get("itc_amount", 0.0))
        txn.matched_rule = classification.get("matched_rule", "invoice")
        txn.confidence = max(txn.confidence, float(classification.get("confidence", 0.7)))
        save_transaction(txn, user_id)
        linked_transaction = txn.to_dict()
        doc["linked_transaction_id"] = txn.id

    _invoices_collection().update_one({"invoice_id": doc["invoice_id"]}, {"$set": doc}, upsert=True)
    return {
        "uploaded": True,
        "invoice": doc,
        "linked_transaction": linked_transaction,
    }


def _extract_fields_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    fields = payload.get("fields")
    if isinstance(fields, list):
        normalized = []
        for idx, f in enumerate(fields, start=1):
            if isinstance(f, dict):
                field_name = _safe_text(f.get("field_name") or f.get("name") or f"Field {idx}")
                normalized.append({
                    "field_id": f.get("field_id") or f"A{idx}",
                    "field_name": field_name,
                    "value": f.get("value"),
                    "status": f.get("status") or "pending",
                })
            else:
                normalized.append({
                    "field_id": f"A{idx}",
                    "field_name": str(f),
                    "value": None,
                    "status": "pending",
                })
        return normalized

    template_name = payload.get("report_name", "Generic Report")
    return [
        {"field_id": "A1", "field_name": f"{template_name} - Name", "value": None, "status": "pending"},
        {"field_id": "A2", "field_name": f"{template_name} - PAN", "value": None, "status": "pending"},
        {"field_id": "A3", "field_name": f"{template_name} - Assessment Year", "value": None, "status": "pending"},
    ]


def _profile_value_map(user_id: str) -> dict[str, Any]:
    profile_doc = _profiles_collection().find_one(
        {"user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0},
    ) or {}
    profile_doc = _decrypt_profile_doc(profile_doc)
    personal = profile_doc.get("personal_info", {}) if isinstance(profile_doc.get("personal_info"), dict) else {}
    business = profile_doc.get("business_info", {}) if isinstance(profile_doc.get("business_info"), dict) else {}
    tax_preferences = profile_doc.get("tax_preferences", {}) if isinstance(profile_doc.get("tax_preferences"), dict) else {}

    full_name = _safe_text(personal.get("full_name") or personal.get("name"))
    first_name = _safe_text(personal.get("first_name"))
    last_name = _safe_text(personal.get("last_name"))

    if full_name and not first_name:
        first_name = full_name.split(" ")[0]
    if full_name and not last_name and len(full_name.split(" ")) > 1:
        last_name = full_name.split(" ")[-1]

    lookup: dict[str, Any] = {
        "name": full_name,
        "full name": full_name,
        "first name": first_name,
        "last name": last_name,
        "pan": personal.get("pan"),
        "aadhaar": personal.get("aadhaar"),
        "dob": personal.get("dob") or personal.get("date_of_birth"),
        "date of birth": personal.get("dob") or personal.get("date_of_birth"),
        "phone": personal.get("phone") or personal.get("mobile"),
        "mobile": personal.get("mobile") or personal.get("phone"),
        "email": personal.get("email"),
        "address": personal.get("address"),
        "business name": business.get("business_name"),
        "entity type": business.get("entity_type"),
        "industry": business.get("industry"),
        "gstin": business.get("gstin"),
        "annual turnover": business.get("annual_turnover"),
        "assessment year": tax_preferences.get("assessment_year"),
        "financial year": tax_preferences.get("financial_year"),
    }

    for key, value in personal.items():
        normalized_key = key.replace("_", " ").strip().lower()
        if normalized_key and normalized_key not in lookup:
            lookup[normalized_key] = value

    for key, value in business.items():
        normalized_key = key.replace("_", " ").strip().lower()
        if normalized_key and normalized_key not in lookup:
            lookup[normalized_key] = value

    bank_accounts = profile_doc.get("bank_accounts", [])
    if isinstance(bank_accounts, list) and bank_accounts:
        first_account = bank_accounts[0]
        if isinstance(first_account, dict):
            lookup["bank account"] = first_account.get("account_number") or first_account.get("number")
            lookup["account number"] = first_account.get("account_number") or first_account.get("number")
            lookup["ifsc"] = first_account.get("ifsc")

    income_sources = profile_doc.get("income_sources", [])
    if isinstance(income_sources, list):
        total_income = 0.0
        for item in income_sources:
            if isinstance(item, dict):
                try:
                    total_income += float(item.get("amount", 0.0) or 0.0)
                except Exception:
                    continue
        if total_income > 0:
            lookup["total income"] = round(total_income, 2)

    return lookup


def _ledger_value_map(user_id: str) -> dict[str, Any]:
    txns = fetch_user_transactions(user_id)
    summary = get_bookkeeping_summary(txns)
    balance = summary.get("balance_summary", {}) if isinstance(summary, dict) else {}
    return {
        "total credits": balance.get("total_credits"),
        "total revenue": balance.get("total_credits"),
        "total debits": balance.get("total_debits"),
        "total expenses": balance.get("total_debits"),
        "net cash flow": balance.get("net_cash_flow"),
        "net profit": balance.get("net_cash_flow"),
        "transaction count": balance.get("transaction_count"),
        "itc": balance.get("total_itc_claimable"),
        "gst": balance.get("total_gst_paid"),
    }


def _task_report_extract_fields(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    extracted_fields = _extract_report_fields(payload)
    filled_entities = _prefill_report_fields_from_profile(user_id, extracted_fields)
    return {
        "report_name": payload.get("report_name", "Generic Report"),
        "fields": extracted_fields,
        "filled_entities": filled_entities,
        "prefill_fields": filled_entities,
        "profile_values": _profile_value_map(user_id),
    }


def _task_report_generate(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    extracted = _extract_report_fields(payload)
    values = {}
    values.update(_profile_value_map(user_id))
    values.update(_ledger_value_map(user_id))
    missing_fields: list[dict[str, Any]] = []
    filled: list[dict[str, Any]] = []

    for field in extracted:
        field_name = _safe_text(field.get("field_name") or "")
        selected_value = field.get("value")

        if selected_value in (None, ""):
            selected_value = _match_value_for_field(field_name, values)

        normalized_field = {
            "field_id": field.get("field_id") or f"A{len(filled) + 1}",
            "field_name": field_name or f"Field {len(filled) + 1}",
            "value": selected_value,
            "status": "filled",
        }

        if selected_value is None:
            normalized_field["status"] = "missing"
            missing_fields.append({
                "field_id": normalized_field["field_id"],
                "field_name": normalized_field["field_name"],
                "prompt": f"Please provide {normalized_field['field_name']}",
                "source": "profile_or_manual",
            })
        else:
            normalized_field["value"] = selected_value

        filled.append(normalized_field)

    prefilled_fields = _prefill_report_fields_from_profile(user_id, filled)

    profile_doc = _profiles_collection().find_one(
        {"user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0},
    ) or {}
    profile_missing_required = _missing_required_profile_fields(_decrypt_profile_doc(profile_doc))

    required_user_inputs = missing_fields[:]
    for field_path in profile_missing_required:
        readable_name = field_path.replace(".", " ").replace("_", " ")
        required_user_inputs.append(
            {
                "field_id": field_path,
                "field_name": readable_name,
                "prompt": f"Update profile with {readable_name}",
                "source": "profile_required",
            }
        )

    report_id = payload.get("report_id") or str(uuid4())
    report_doc = {
        "report_id": report_id,
        "user_id": user_id,
        "status": "generated" if not required_user_inputs else "needs_user_input",
        "report_name": payload.get("report_name", "Generic Report"),
        "fields": filled,
        "missing_fields": missing_fields,
        "required_user_inputs": required_user_inputs,
        "profile_missing_required": profile_missing_required,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _reports_collection().update_one({"report_id": report_id}, {"$set": report_doc}, upsert=True)

    return {
        "report_id": report_id,
        "status": report_doc["status"],
        "fields": filled,
        "filled_entities": prefilled_fields,
        "missing_fields": missing_fields,
        "required_user_inputs": required_user_inputs,
    }


def _task_report_status(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_id = payload.get("report_id")
    if not report_id:
        return {"found": False, "error": "report_id is required"}

    report = _reports_collection().find_one({"report_id": report_id, "user_id": user_id}, {"_id": 0})
    if not report:
        return {"found": False, "report_id": report_id}

    return {"found": True, "report": report}


def _task_report_view(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_id = payload.get("report_id")
    if not report_id:
        return {"found": False, "error": "report_id is required"}

    report = _reports_collection().find_one({"report_id": report_id, "user_id": user_id}, {"_id": 0})
    if not report:
        return {"found": False, "report_id": report_id}

    fields = report.get("fields", []) if isinstance(report.get("fields"), list) else []
    filled_entities = [
        field for field in fields
        if isinstance(field, dict) and field.get("value") not in (None, "")
    ]
    missing_entities = [
        field for field in fields
        if isinstance(field, dict) and field.get("value") in (None, "")
    ]

    return {
        "found": True,
        "report_id": report_id,
        "report_name": report.get("report_name"),
        "status": report.get("status"),
        "report": report,
        "filled_entities": filled_entities,
        "missing_entities": missing_entities,
        "required_user_inputs": report.get("required_user_inputs", []),
        "missing_fields": report.get("missing_fields", []),
        "profile_missing_required": report.get("profile_missing_required", []),
    }


def _task_report_prefill(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    profile_result = get_profile(user_id)
    profile_doc = profile_result.get("profile", {}) if isinstance(profile_result, dict) else {}
    user_doc = profile_result.get("user", {}) if isinstance(profile_result, dict) else {}

    profile_values = _profile_value_map(user_id)
    ledger_values = _ledger_value_map(user_id)

    form_fields = [
        {"field_id": "full_name", "field_name": "Full Name", "value": profile_values.get("name") or profile_values.get("full name"), "source": "profile", "status": "filled"},
        {"field_id": "phone", "field_name": "Phone", "value": profile_values.get("phone") or profile_values.get("mobile"), "source": "profile", "status": "filled"},
        {"field_id": "email", "field_name": "Email", "value": profile_values.get("email"), "source": "profile", "status": "filled"},
        {"field_id": "pan", "field_name": "PAN", "value": profile_values.get("pan"), "source": "profile", "status": "filled"},
        {"field_id": "aadhaar", "field_name": "Aadhaar", "value": profile_values.get("aadhaar"), "source": "profile", "status": "filled"},
        {"field_id": "business_name", "field_name": "Business Name", "value": profile_values.get("business name"), "source": "profile", "status": "filled"},
        {"field_id": "entity_type", "field_name": "Entity Type", "value": profile_values.get("entity type"), "source": "profile", "status": "filled"},
        {"field_id": "gstin", "field_name": "GSTIN", "value": profile_values.get("gstin"), "source": "profile", "status": "filled"},
        {"field_id": "annual_turnover", "field_name": "Annual Turnover", "value": profile_values.get("annual turnover"), "source": "profile", "status": "filled"},
        {"field_id": "net_cash_flow", "field_name": "Net Cash Flow", "value": ledger_values.get("net cash flow"), "source": "ledger", "status": "filled"},
        {"field_id": "total_income", "field_name": "Total Income", "value": profile_values.get("total income") or ledger_values.get("total revenue"), "source": "ledger", "status": "filled"},
    ]

    return {
        "profile": profile_doc,
        "user": user_doc,
        "prefill_fields": form_fields,
        "profile_values": profile_values,
        "ledger_values": ledger_values,
    }


def _analyze_fields(fields: list[dict[str, Any]], profile_values: dict[str, Any]) -> dict[str, Any]:
    errors = []
    warnings = []
    suggestions = []

    for field in fields:
        field_id = field.get("field_id")
        field_name = _safe_text(field.get("field_name", ""))
        value = field.get("value")
        value_text = _safe_text(value)
        lower_name = field_name.lower()

        if value in (None, "") or value_text == "":
            errors.append({
                "field_id": field_id,
                "message": f"{field_name} is required",
            })
            continue

        if "pan" in lower_name:
            pan = value_text.upper()
            if not PAN_REGEX.match(pan):
                errors.append({"field_id": field_id, "message": "PAN format is invalid"})
            profile_pan = _safe_text(profile_values.get("pan")).upper()
            if profile_pan and pan != profile_pan:
                warnings.append({"field_id": field_id, "message": "PAN differs from profile PAN"})

        if "aadhaar" in lower_name:
            ad = "".join(ch for ch in value_text if ch.isdigit())
            if not AADHAAR_REGEX.match(ad):
                errors.append({"field_id": field_id, "message": "Aadhaar should be 12 digits"})

        if "gstin" in lower_name:
            gstin = value_text.upper()
            if not GSTIN_REGEX.match(gstin):
                errors.append({"field_id": field_id, "message": "GSTIN format is invalid"})

        if "email" in lower_name and not EMAIL_REGEX.match(value_text):
            warnings.append({"field_id": field_id, "message": "Email format looks invalid"})

        if any(token in lower_name for token in ("phone", "mobile", "contact")):
            digits = "".join(ch for ch in value_text if ch.isdigit())
            if not PHONE_REGEX.match(digits):
                warnings.append({"field_id": field_id, "message": "Phone number format looks invalid"})

        if "assessment year" in lower_name and not ASSESSMENT_YEAR_REGEX.match(value_text):
            warnings.append({"field_id": field_id, "message": "Assessment year should look like YYYY-YY"})

        if any(token in lower_name for token in ("date", "dob", "birth")):
            try:
                date_parser.parse(value_text, dayfirst=True)
            except Exception:
                errors.append({"field_id": field_id, "message": f"{field_name} has invalid date format"})

        if any(token in lower_name for token in ("amount", "total", "income", "expense", "revenue", "cash flow", "profit")):
            numeric = re.sub(r"[^0-9.\-]", "", value_text)
            if numeric:
                try:
                    float(numeric)
                except Exception:
                    errors.append({"field_id": field_id, "message": f"{field_name} should be numeric"})

    if not errors and not warnings:
        suggestions.append("Report looks consistent and ready for submission.")
    elif errors:
        suggestions.append("Fix required-field and format errors before submission.")

    if warnings:
        suggestions.append("Review warnings and confirm values against profile records.")

    return {"errors": errors, "warnings": warnings, "suggestions": suggestions}


def _task_report_analyze(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []

    if payload.get("report_id"):
        report = _reports_collection().find_one({"report_id": payload["report_id"], "user_id": user_id}, {"_id": 0})
        if report:
            fields = report.get("fields", fields)

    if not fields:
        if payload.get("file_path") and os.path.exists(payload["file_path"]):
            fields = extract_filled_fields_from_pdf(payload["file_path"])
        else:
            fields = _extract_report_fields(payload)

    profile_values = _profile_value_map(user_id)
    analysis = _analyze_fields(fields, profile_values)
    return {
        "report_analysis": analysis,
        "fields_analyzed": len(fields),
    }


def _task_report_validate(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    analysis = _task_report_analyze(user_id, payload).get("report_analysis", {})
    errors = analysis.get("errors", [])
    warnings = analysis.get("warnings", [])
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "suggestions": analysis.get("suggestions", []),
    }


def _task_deadline_add(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    deadline_id = payload.get("deadline_id") or str(uuid4())
    doc = {
        "deadline_id": deadline_id,
        "user_id": user_id,
        "type": payload.get("type", "compliance"),
        "title": payload.get("title", "Compliance deadline"),
        "due_date": payload.get("due_date"),
        "status": payload.get("status", "pending"),
        "submitted": bool(payload.get("submitted", False)),
        "meta": payload.get("meta", {}),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _deadlines_collection().update_one({"deadline_id": deadline_id}, {"$set": doc}, upsert=True)
    return {"saved": True, "deadline": doc}


def _task_deadline_get(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    items = list(_deadlines_collection().find({"user_id": user_id}, {"_id": 0}).sort("due_date", 1))
    return {"deadlines": items, "count": len(items)}


def _task_deadline_delete(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    deadline_id = payload.get("deadline_id")
    if not deadline_id:
        return {"deleted": False, "error": "deadline_id is required"}

    result = _deadlines_collection().delete_one({"deadline_id": deadline_id, "user_id": user_id})
    return {"deleted": result.deleted_count > 0, "deadline_id": deadline_id}


def _task_deadline_send_reminders(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    limit_raw = payload.get("limit", 50)
    try:
        limit = max(1, min(int(limit_raw), 500))
    except Exception:
        limit = 50

    queued_new = scan_deadlines_once(user_id=user_id)
    sent = dispatch_queued_notifications(limit=limit, user_id=user_id)
    still_queued = _get_db()["notifications"].count_documents({"user_id": user_id, "status": "queued"})

    return {
        "user_id": user_id,
        "queued_new": queued_new,
        "sent": sent,
        "still_queued": still_queued,
        "limit": limit,
    }


def _task_assistant_chat(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    message = payload.get("message") or payload.get("query")
    if not message:
        return {"answered": False, "error": "message is required"}

    lowered = str(message).lower()
    in_scope = any(keyword in lowered for keyword in ASSISTANT_SCOPE_KEYWORDS)
    if not in_scope:
        return {
            "answered": False,
            "error": "Query is out of scope. Ask tax, finance, bookkeeping, report, or compliance questions.",
        }

    response = execute_goal(user_id, message)
    return {"answered": True, "response": response}


TASK_HANDLERS = {
    "create_profile": _task_create_profile,
    "get_profile": _task_get_profile,
    "update_profile": _task_update_profile,
    "delete_profile": _task_delete_profile,
    "bookkeeping_add_entry": _task_bookkeeping_add_entry,
    "bookkeeping_get_ledger": _task_bookkeeping_get_ledger,
    "bookkeeping_update_entry": _task_bookkeeping_update_entry,
    "bookkeeping_upload_statement": _task_bookkeeping_upload_statement,
    "bookkeeping_upload_invoice": _task_bookkeeping_upload_invoice,
    "report_extract_fields": _task_report_extract_fields,
    "report_generate": _task_report_generate,
    "report_status": _task_report_status,
    "report_view": _task_report_view,
    "report_prefill": _task_report_prefill,
    "report_analyze": _task_report_analyze,
    "report_validate": _task_report_validate,
    "deadline_add": _task_deadline_add,
    "deadline_get": _task_deadline_get,
    "deadline_delete": _task_deadline_delete,
    "deadline_send_reminders": _task_deadline_send_reminders,
    "assistant_chat": _task_assistant_chat,
}


def _execute_sync(task_name: str, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    handler = TASK_HANDLERS.get(task_name)
    if handler is None:
        return {
            "status": "error",
            "task_name": task_name,
            "user_id": user_id,
            "data": None,
            "errors": [f"Unsupported task_name: {task_name}"],
            "warnings": [],
            "correlation_id": str(uuid4()),
        }

    try:
        data = handler(user_id, payload)
        return {
            "status": "success",
            "task_name": task_name,
            "user_id": user_id,
            "data": data,
            "errors": [],
            "warnings": [],
            "correlation_id": str(uuid4()),
        }
    except Exception as exc:
        return {
            "status": "error",
            "task_name": task_name,
            "user_id": user_id,
            "data": None,
            "errors": [str(exc)],
            "warnings": [],
            "correlation_id": str(uuid4()),
        }


def _run_job(job_id: str, task_name: str, user_id: str, payload: dict[str, Any]) -> None:
    _jobs_collection().update_one(
        {"job_id": job_id},
        {"$set": {"status": "running", "updated_at": _now_iso()}},
    )
    result = _execute_sync(task_name=task_name, user_id=user_id, payload=payload)
    terminal_status = "completed" if result.get("status") == "success" else "failed"
    _jobs_collection().update_one(
        {"job_id": job_id},
        {
            "$set": {
                "status": terminal_status,
                "result": result,
                "updated_at": _now_iso(),
            }
        },
    )


def execute_task(
    *,
    task_name: str,
    user_id: str,
    payload: dict[str, Any],
    mode: str,
    idempotency_key: str | None,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    if mode == "sync":
        return _execute_sync(task_name=task_name, user_id=user_id, payload=payload)

    if idempotency_key:
        existing = _jobs_collection().find_one(
            {
                "user_id": user_id,
                "task_name": task_name,
                "idempotency_key": idempotency_key,
            },
            {"_id": 0, "job_id": 1, "status": 1},
        )
        if existing and existing.get("job_id"):
            return {
                "status": "accepted",
                "task_name": task_name,
                "user_id": user_id,
                "data": {"reused": True, "existing_status": existing.get("status")},
                "errors": [],
                "warnings": ["Reused existing async job due to idempotency_key."],
                "correlation_id": str(uuid4()),
                "job_id": existing.get("job_id"),
            }

    job_id = str(uuid4())
    job_doc = {
        "job_id": job_id,
        "task_name": task_name,
        "user_id": user_id,
        "payload": payload,
        "mode": "async",
        "status": "queued",
        "idempotency_key": idempotency_key or "",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _jobs_collection().insert_one(job_doc)
    background_tasks.add_task(_run_job, job_id, task_name, user_id, payload)

    return {
        "status": "accepted",
        "task_name": task_name,
        "user_id": user_id,
        "data": None,
        "errors": [],
        "warnings": [],
        "correlation_id": str(uuid4()),
        "job_id": job_id,
    }


def get_job_status(job_id: str) -> dict[str, Any]:
    doc = _jobs_collection().find_one({"job_id": job_id}, {"_id": 0})
    if not doc:
        return {
            "found": False,
            "job_id": job_id,
        }
    return {
        "found": True,
        "job": doc,
    }


def create_profile(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _task_create_profile(user_id, payload)


def get_profile(user_id: str) -> dict[str, Any]:
    return _task_get_profile(user_id, {})


def update_profile(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _task_update_profile(user_id, payload)


def delete_profile(user_id: str) -> dict[str, Any]:
    return _task_delete_profile(user_id, {})


def bookkeeping_add_entry(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _task_bookkeeping_add_entry(user_id, payload)


def bookkeeping_get_ledger(user_id: str) -> dict[str, Any]:
    return _task_bookkeeping_get_ledger(user_id, {})


def bookkeeping_update_entry(user_id: str, entry_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    return _task_bookkeeping_update_entry(user_id, {"entry_id": entry_id, "updates": updates})


def bookkeeping_upload_statement_from_path(user_id: str, file_path: str) -> dict[str, Any]:
    return _task_bookkeeping_upload_statement(user_id, {"file_path": file_path})


def bookkeeping_upload_invoice(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _task_bookkeeping_upload_invoice(user_id, payload)


def report_extract_fields(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _task_report_extract_fields(user_id, payload)


def report_generate(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _task_report_generate(user_id, payload)


def report_status(user_id: str, report_id: str) -> dict[str, Any]:
    return _task_report_status(user_id, {"report_id": report_id})


def report_view(user_id: str, report_id: str) -> dict[str, Any]:
    return _task_report_view(user_id, {"report_id": report_id})


def report_prefill(user_id: str) -> dict[str, Any]:
    return _task_report_prefill(user_id, {})


def report_analyze(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _task_report_analyze(user_id, payload)


def report_validate(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _task_report_validate(user_id, payload)


def deadline_add(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _task_deadline_add(user_id, payload)


def deadline_get(user_id: str) -> dict[str, Any]:
    return _task_deadline_get(user_id, {})


def deadline_delete(user_id: str, deadline_id: str) -> dict[str, Any]:
    return _task_deadline_delete(user_id, {"deadline_id": deadline_id})


def deadline_send_reminders(user_id: str, limit: int = 50) -> dict[str, Any]:
    return _task_deadline_send_reminders(user_id, {"limit": limit})


def assistant_chat(user_id: str, message: str) -> dict[str, Any]:
    return _task_assistant_chat(user_id, {"message": message})
