from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import os
import re
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Any

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
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
from finpilot.services.parsers.itr1_template import ITR1_REPORT_NAME, itr1_template_fields
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
    "deadline",
    "due",
    "reminder",
    "calendar",
    "bookkeeping",
    "ledger",
    "transaction",
    "transactions",
    "invoice",
    "correction",
    "corrections",
    "profit",
    "expense",
    "cashflow",
    "report",
    "form",
    "itr",
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

SUPPORTED_ITR_REPORT_ALIASES = {"ITR1", "ITR-1"}

EMPTY_FIELD_SENTINELS = {None, "", "-", "--", "---", "—", "N/A", "NA", "null", "None"}

ITR1_FIELD_VALUE_KEYS: dict[str, tuple[str, ...]] = {
    "A1": ("pan",),
    "A2": ("first name",),
    "A2a": ("middle name",),
    "A3": ("last name",),
    "A4": ("date of birth", "dob"),
    "A5": ("aadhaar",),
    "A6a": ("phone", "mobile"),
    "A6b": ("secondary mobile",),
    "A7a": ("email",),
    "A7b": ("secondary email",),
    "A8a": ("address flat", "flat door block", "address line 1"),
    "A9a": ("address premises", "building village"),
    "A10a": ("address street", "road street post office", "street"),
    "A11a": ("address city", "town city district", "city"),
    "A12a": ("address state", "state"),
    "A13a": ("address country", "country"),
    "A14a": ("address pin code", "pin code"),
    "A8b": ("secondary address flat",),
    "A9b": ("secondary address premises",),
    "A10b": ("secondary address street",),
    "A11b": ("secondary address city",),
    "A12b": ("secondary address state",),
    "A13b": ("secondary address country",),
    "A14b": ("secondary address pin code",),
    "A15": ("filed under section", "return filing section", "filing section"),
    "A16": ("filed in response to notice", "notice section"),
    "A17": ("nature of employment", "employment type", "occupation"),
    "A20": ("opting out of new tax regime", "opt out new tax regime", "old regime opted"),
    "PART_A_GENERAL_INFORMATION.A21.general": ("filing under seventh proviso", "seventh proviso filing", "seventh proviso applicable"),
    "PART_A_GENERAL_INFORMATION.A21.i": ("foreign travel expenditure",),
    "PART_A_GENERAL_INFORMATION.A21.ii": ("electricity expenditure",),
    "PART_A_GENERAL_INFORMATION.A21.iii": ("other prescribed conditions",),
    "PART_A_GENERAL_INFORMATION.A22.general": ("representative assessee",),
    "PART_A_GENERAL_INFORMATION.A22.name": ("representative name",),
    "PART_A_GENERAL_INFORMATION.A22.email": ("representative email",),
    "PART_A_GENERAL_INFORMATION.A22.contact": ("representative contact",),
    "PART_B_GROSS_TOTAL_INCOME.B1.total": ("salary income", "income from salary", "income salaries"),
    "B3": ("income from other sources", "other income"),
    "B4": ("total income", "total revenue"),
    "C1": ("total deductions", "deductions total"),
    "C2": ("total income",),
    "D11": ("total tax liability", "total tax fee interest"),
    "D12": ("taxes paid",),
    "D14": ("refund amount",),
    "IFS": ("ifsc",),
    "PART_E_OTHER_INFORMATION.bank_details.bank_name": ("bank name",),
    "PART_E_OTHER_INFORMATION.bank_details.account_number": ("account number", "bank account"),
    "PART_E_OTHER_INFORMATION.bank_details.account_type": ("account type",),
    "PART_E_OTHER_INFORMATION.bank_details.refund_flag": ("selected for refund", "refund flag"),
    "VERIFICATION.capacity": ("verification capacity", "capacity"),
    "VERIFICATION.name": ("full name", "name"),
    "VERIFICATION.date": ("today date",),
}

ITR1_FIELD_TO_PROFILE_PATH: dict[str, str] = {
    "A1": "personal_info.pan",
    "A2": "personal_info.first_name",
    "A2a": "personal_info.middle_name",
    "A3": "personal_info.last_name",
    "A4": "personal_info.dob",
    "A5": "personal_info.aadhaar",
    "A6a": "personal_info.phone",
    "A6b": "personal_info.secondary_phone",
    "A7a": "personal_info.email",
    "A7b": "personal_info.secondary_email",
    "A8a": "personal_info.address.flat",
    "A9a": "personal_info.address.premises",
    "A10a": "personal_info.address.street",
    "A11a": "personal_info.address.city",
    "A12a": "personal_info.address.state",
    "A13a": "personal_info.address.country",
    "A14a": "personal_info.address.pin_code",
    "A8b": "personal_info.secondary_address.flat",
    "A9b": "personal_info.secondary_address.premises",
    "A10b": "personal_info.secondary_address.street",
    "A11b": "personal_info.secondary_address.city",
    "A12b": "personal_info.secondary_address.state",
    "A13b": "personal_info.secondary_address.country",
    "A14b": "personal_info.secondary_address.pin_code",
    "A15": "tax_preferences.filed_under_section",
    "A16": "tax_preferences.notice_section",
    "A17": "personal_info.occupation",
    "A20": "tax_preferences.opt_out_new_tax_regime",
    "PART_A_GENERAL_INFORMATION.A21.general": "tax_preferences.seventh_proviso_applicable",
    "PART_A_GENERAL_INFORMATION.A21.i": "tax_preferences.foreign_travel_expenditure",
    "PART_A_GENERAL_INFORMATION.A21.ii": "tax_preferences.electricity_expenditure",
    "PART_A_GENERAL_INFORMATION.A21.iii": "tax_preferences.other_prescribed_conditions",
    "PART_A_GENERAL_INFORMATION.A22.general": "tax_preferences.representative_assessee",
    "PART_A_GENERAL_INFORMATION.A22.name": "tax_preferences.representative_name",
    "PART_A_GENERAL_INFORMATION.A22.email": "tax_preferences.representative_email",
    "PART_A_GENERAL_INFORMATION.A22.contact": "tax_preferences.representative_contact",
    "IFS": "bank_accounts.0.ifsc",
    "PART_E_OTHER_INFORMATION.bank_details.bank_name": "bank_accounts.0.bank_name",
    "PART_E_OTHER_INFORMATION.bank_details.account_number": "bank_accounts.0.account_number",
    "PART_E_OTHER_INFORMATION.bank_details.account_type": "bank_accounts.0.account_type",
    "PART_E_OTHER_INFORMATION.bank_details.refund_flag": "bank_accounts.0.refund_flag",
    "VERIFICATION.capacity": "tax_preferences.verification_capacity",
    "VERIFICATION.name": "personal_info.full_name",
}

ITR1_MAJORITY_DEFAULT_VALUES: dict[str, Any] = {
    "A13a": "India",
    "A13b": "India",
    "A15": "139(1)",
    "A16": "Not Applicable",
    "A17": "Private Sector Employee",
    "A20": "No",
    "PART_A_GENERAL_INFORMATION.A21.general": "No",
    "PART_A_GENERAL_INFORMATION.A21.i": "0",
    "PART_A_GENERAL_INFORMATION.A21.ii": "0",
    "PART_A_GENERAL_INFORMATION.A21.iii": "No",
    "PART_A_GENERAL_INFORMATION.A22.general": "No",
    "PART_E_OTHER_INFORMATION.bank_details.account_type": "Savings",
    "PART_E_OTHER_INFORMATION.bank_details.refund_flag": "Yes",
    "VERIFICATION.capacity": "Self",
}


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


def _resolve_transaction_date(
    user_id: str,
    *,
    linked_transaction_id: str | None,
    invoice_date_raw: str | None,
) -> datetime:
    if linked_transaction_id:
        txn = _get_db()["transactions"].find_one(
            {"_id": linked_transaction_id, "user_id": user_id},
            {"_id": 0, "date": 1},
        )
        if txn and txn.get("date"):
            try:
                return _parse_datetime(str(txn["date"]))
            except Exception:
                pass

    if invoice_date_raw:
        return _parse_datetime(invoice_date_raw)

    return datetime.now()


def _next_financial_year_end_from_date(transaction_date: datetime) -> datetime:
    return datetime(transaction_date.year if transaction_date.month <= 3 else transaction_date.year + 1, 3, 31)


def _transaction_deadline_due_date(transaction_date: datetime) -> datetime:
    return transaction_date + relativedelta(months=+6)


def _sync_transaction_deadlines(user_id: str) -> dict[str, int]:
    txns = list(
        _get_db()["transactions"].find(
            {"user_id": user_id},
            {
                "_id": 1,
                "amount": 1,
                "type": 1,
                "party": 1,
                "date": 1,
                "source": 1,
                "category": 1,
                "sub_category": 1,
            },
        )
    )

    created = 0
    updated = 0

    for txn in txns:
        txn_id = str(txn.get("_id") or "").strip()
        if not txn_id:
            continue

        txn_date = _parse_datetime(str(txn.get("date") or ""))
        due_date = _transaction_deadline_due_date(txn_date)
        now_iso = _now_iso()
        deadline_id = f"transaction-{txn_id}"
        existing = _deadlines_collection().find_one(
            {"deadline_id": deadline_id, "user_id": user_id},
            {"_id": 0, "status": 1, "submitted": 1, "created_at": 1},
        )

        status = existing.get("status") if isinstance(existing, dict) and existing.get("status") else "pending"
        submitted = bool(existing.get("submitted")) if isinstance(existing, dict) else False

        doc = {
            "deadline_id": deadline_id,
            "user_id": user_id,
            "type": "transaction_review",
            "title": f"Transaction review - {txn.get('party') or 'Unknown party'}",
            "due_date": due_date.date().isoformat(),
            "status": status,
            "submitted": submitted,
            "meta": {
                "source": "transaction_auto_deadline",
                "transaction_id": txn_id,
                "transaction_date": txn_date.date().isoformat(),
                "transaction_month": txn_date.strftime("%B %Y"),
                "deadline_rule": "6_months_from_transaction_date",
                "amount": float(txn.get("amount") or 0.0),
                "transaction_type": str(txn.get("type") or "").lower() or "unknown",
                "party": txn.get("party") or "Unknown",
                "category": txn.get("category") or "Uncategorized",
                "sub_category": txn.get("sub_category") or "Uncategorized",
                "txn_source": txn.get("source") or "unknown",
            },
            "updated_at": now_iso,
        }

        result = _deadlines_collection().update_one(
            {"deadline_id": deadline_id, "user_id": user_id},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": now_iso},
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            created += 1
        elif result.modified_count > 0:
            updated += 1

    return {"created": created, "updated": updated}


def _infer_invoice_financial_year_end(transaction_date: datetime) -> datetime:
    api_key = config.OPENAI_API_KEY
    deterministic = _next_financial_year_end_from_date(transaction_date)
    if not api_key:
        return deterministic

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You calculate Indian financial year ends. "
                        "Given a transaction date, return only JSON with key financial_year_end in ISO date format. "
                        "Use the next financial year end after the transaction date, ending on March 31."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Transaction date: {transaction_date.date().isoformat()}",
                },
            ],
        )
        content = response.choices[0].message.content or ""
        parsed = json.loads(content)
        raw_financial_year_end = _safe_text(parsed.get("financial_year_end"))
        if raw_financial_year_end:
            return datetime.fromisoformat(raw_financial_year_end)
    except Exception:
        pass

    return deterministic


def _infer_invoice_due_date(extracted: dict[str, Any], fallback_date: datetime) -> datetime:
    raw_text = _safe_text(extracted.get("raw_text"))

    explicit_patterns = [
        r"(?i)(?:due\s*date|payment\s*due|pay\s*by|due\s*on)\s*[:\-]?\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4})",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, raw_text)
        if match:
            try:
                return date_parser.parse(match.group(1), dayfirst=True)
            except Exception:
                continue

    relative_patterns = [
        r"(?i)due\s+in\s+([0-9]{1,3})\s+days?",
        r"(?i)payable\s+within\s+([0-9]{1,3})\s+days?",
        r"(?i)net\s+([0-9]{1,3})",
    ]
    for pattern in relative_patterns:
        match = re.search(pattern, raw_text)
        if match:
            try:
                days = int(match.group(1))
                return fallback_date + timedelta(days=max(1, days))
            except Exception:
                continue

    invoice_date_raw = extracted.get("invoice_date")
    if invoice_date_raw:
        try:
            invoice_date = date_parser.parse(str(invoice_date_raw), dayfirst=True)
            return invoice_date + timedelta(days=30)
        except Exception:
            pass

    return fallback_date + timedelta(days=30)


def _schedule_invoice_deadline(
    user_id: str,
    *,
    invoice: dict[str, Any],
    linked_transaction_id: str | None,
) -> dict[str, Any]:
    transaction_date = _resolve_transaction_date(
        user_id,
        linked_transaction_id=linked_transaction_id,
        invoice_date_raw=invoice.get("date"),
    )
    financial_year_end = _infer_invoice_financial_year_end(transaction_date)
    due_date = financial_year_end
    deadline_id = invoice.get("invoice_id") or str(uuid4())
    deadline_doc = {
        "user_id": user_id,
        "deadline_id": f"invoice-{deadline_id}",
        "type": "invoice_payment",
        "title": f"Invoice Payment FY End - {invoice.get('party', 'Unknown')}",
        "due_date": due_date.date().isoformat(),
        "status": "pending",
        "submitted": False,
        "meta": {
            "source": "bookkeeping_invoice_upload",
            "invoice_id": invoice.get("invoice_id"),
            "invoice_date": invoice.get("date"),
            "transaction_date": transaction_date.date().isoformat(),
            "linked_transaction_id": linked_transaction_id,
            "amount": invoice.get("amount", 0.0),
            "party": invoice.get("party", "Unknown"),
            "financial_year_end": financial_year_end.date().isoformat(),
        },
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    _deadlines_collection().update_one(
        {"deadline_id": deadline_doc["deadline_id"], "user_id": user_id},
        {"$set": deadline_doc},
        upsert=True,
    )

    queued_new = scan_deadlines_once(user_id=user_id, force_queue=True)
    sent_now = dispatch_queued_notifications(limit=50, user_id=user_id)
    return {
        "deadline": deadline_doc,
        "queued_new": queued_new,
        "sent_now": sent_now,
    }


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if _is_empty_field_value(value):
            continue
        return value
    return None


def _normalize_yes_no(value: Any, default: str | None = None) -> str | None:
    if _is_empty_field_value(value):
        return default
    if isinstance(value, bool):
        return "Yes" if value else "No"

    text = _safe_text(value).lower()
    if text in {"yes", "y", "true", "1", "x", "checked", "applicable"}:
        return "Yes"
    if text in {"no", "n", "false", "0", "na", "n/a", "not applicable", "none", "unchecked"}:
        return "No"
    return default if default is not None else _safe_text(value)


def _is_empty_field_value(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() in EMPTY_FIELD_SENTINELS

    # Nested objects should not be treated as scalar field values.
    if isinstance(value, (dict, list, tuple, set)):
        return len(value) == 0

    try:
        return value in EMPTY_FIELD_SENTINELS
    except TypeError:
        return False


def _majority_default_for_field(field_id: str, field_name: str, values: dict[str, Any]):
    if field_id in {"A13a", "A13b"}:
        return _first_non_empty(values.get("country"), ITR1_MAJORITY_DEFAULT_VALUES.get(field_id))

    if field_id == "A17":
        return _first_non_empty(
            values.get("nature of employment"),
            values.get("employment type"),
            values.get("occupation"),
            ITR1_MAJORITY_DEFAULT_VALUES.get(field_id),
        )

    if field_id == "A20":
        return _normalize_yes_no(
            _first_non_empty(
                values.get("opting out of new tax regime"),
                values.get("opt out new tax regime"),
                values.get("old regime opted"),
            ),
            default=str(ITR1_MAJORITY_DEFAULT_VALUES.get(field_id)),
        )

    if field_id == "PART_A_GENERAL_INFORMATION.A21.general":
        return _normalize_yes_no(
            _first_non_empty(
                values.get("filing under seventh proviso"),
                values.get("seventh proviso filing"),
                values.get("seventh proviso applicable"),
            ),
            default=str(ITR1_MAJORITY_DEFAULT_VALUES.get(field_id)),
        )

    if field_id == "PART_A_GENERAL_INFORMATION.A22.general":
        representative_present = any(
            not _is_empty_field_value(values.get(key))
            for key in ("representative name", "representative email", "representative contact")
        )
        return "Yes" if representative_present else ITR1_MAJORITY_DEFAULT_VALUES.get(field_id)

    if field_id == "PART_E_OTHER_INFORMATION.bank_details.refund_flag":
        return _normalize_yes_no(
            _first_non_empty(values.get("selected for refund"), values.get("refund flag")),
            default=str(ITR1_MAJORITY_DEFAULT_VALUES.get(field_id)),
        )

    if field_id in {
        "A15",
        "A16",
        "PART_A_GENERAL_INFORMATION.A21.i",
        "PART_A_GENERAL_INFORMATION.A21.ii",
        "PART_A_GENERAL_INFORMATION.A21.iii",
        "PART_E_OTHER_INFORMATION.bank_details.account_type",
        "VERIFICATION.capacity",
    }:
        return ITR1_MAJORITY_DEFAULT_VALUES.get(field_id)

    if "opting out" in field_name.lower() and field_id not in ITR1_MAJORITY_DEFAULT_VALUES:
        return "No"

    return None


def _normalize_report_name(report_name: Any) -> str:
    text = _safe_text(report_name or ITR1_REPORT_NAME)
    compact = text.upper().replace("_", "").replace("-", "").replace(" ", "")
    if compact in {"", "ITR1"}:
        return ITR1_REPORT_NAME
    if text.upper() in SUPPORTED_ITR_REPORT_ALIASES:
        return ITR1_REPORT_NAME
    raise ValueError("Only ITR-1 report template is supported for now.")


def _itr1_template_base_fields() -> list[dict[str, Any]]:
    return itr1_template_fields()


def _merge_field_values(
    base_fields: list[dict[str, Any]],
    incoming_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not incoming_fields:
        return base_fields

    id_to_index = {
        _safe_text(field.get("field_id")): index
        for index, field in enumerate(base_fields)
        if _safe_text(field.get("field_id"))
    }
    name_to_index = {
        _normalize_key(_safe_text(field.get("field_name"))): index
        for index, field in enumerate(base_fields)
        if _safe_text(field.get("field_name"))
    }

    for incoming in incoming_fields:
        field_id = _safe_text(incoming.get("field_id") or incoming.get("id"))
        field_name = _safe_text(incoming.get("field_name") or incoming.get("name"))
        value = incoming.get("value")

        if _is_empty_field_value(value):
            continue

        target_index = id_to_index.get(field_id)
        if target_index is None and field_name:
            target_index = name_to_index.get(_normalize_key(field_name))
        if target_index is None:
            continue

        target = base_fields[target_index]
        target["value"] = value
        target["status"] = "filled"
        target["source"] = incoming.get("source") or target.get("source") or "manual"

    return base_fields


def _extract_report_fields(payload: dict[str, Any]) -> list[dict[str, Any]]:
    report_name = _normalize_report_name(payload.get("report_name"))
    normalized_payload = {**payload, "report_name": report_name}
    base_fields = _itr1_template_base_fields()

    provided_fields = _coerce_field_list(normalized_payload.get("fields"))
    base_fields = _merge_field_values(base_fields, provided_fields)

    file_path = payload.get("file_path")
    if file_path and os.path.exists(file_path):
        parsed = extract_fields_from_report_pdf(file_path)
        fields = parsed.get("fields", [])
        if fields:
            refined = _refine_report_fields_with_ai(report_name, parsed.get("template_text", ""), fields)
            base_fields = _merge_field_values(base_fields, _coerce_field_list(refined))

    template_text = payload.get("report_template_text")
    if template_text:
        fields = extract_fields_from_template_text(str(template_text))
        if fields:
            refined = _refine_report_fields_with_ai(report_name, str(template_text), fields)
            base_fields = _merge_field_values(base_fields, _coerce_field_list(refined))

    for field in base_fields:
        field["status"] = "filled" if not _is_empty_field_value(field.get("value")) else "pending"

    return base_fields


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
        field_id = _safe_text(field.get("field_id") or field.get("id") or "")
        existing_value = field.get("value")
        selected_value = existing_value

        if _is_empty_field_value(selected_value):
            selected_value = _resolve_prefill_value(field_id, field_name, combined_values)

        status = field.get("status") or "pending"
        if not _is_empty_field_value(selected_value):
            status = "filled"

        filled.append({
            "field_id": field_id or f"A{len(filled) + 1}",
            "field_name": field_name or f"Field {len(filled) + 1}",
            "value": selected_value,
            "status": status,
            "source": field.get("source") or ("profile" if not _is_empty_field_value(selected_value) else "manual"),
            "section": field.get("section"),
            "path": field.get("path"),
            "required": field.get("required", True),
            "prompt": field.get("prompt") or f"Please provide {field_name or f'Field {len(filled) + 1}'}",
        })

    return filled


def _resolve_prefill_value(field_id: str, field_name: str, values: dict[str, Any]):
    mapped_keys = ITR1_FIELD_VALUE_KEYS.get(field_id, ())
    for key in mapped_keys:
        if key == "today date":
            return datetime.now().date().isoformat()
        mapped_value = values.get(key)
        if not _is_empty_field_value(mapped_value):
            return mapped_value

    fuzzy_value = _match_value_for_field(field_name, values)
    if not _is_empty_field_value(fuzzy_value):
        return fuzzy_value

    return _majority_default_for_field(field_id, field_name, values)


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
        doc["date"] = txn.date.isoformat()

    _invoices_collection().update_one({"invoice_id": doc["invoice_id"]}, {"$set": doc}, upsert=True)
    deadline_result = _schedule_invoice_deadline(
        user_id,
        invoice=doc,
        linked_transaction_id=doc.get("linked_transaction_id"),
    )
    return {
        "uploaded": True,
        "invoice": doc,
        "linked_transaction": linked_transaction,
        "deadline": deadline_result.get("deadline"),
        "reminders_queued": deadline_result.get("queued_new", 0),
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
    address = personal.get("address", {}) if isinstance(personal.get("address"), dict) else {}
    secondary_address = personal.get("secondary_address", {}) if isinstance(personal.get("secondary_address"), dict) else {}
    bank_accounts = profile_doc.get("bank_accounts", [])
    first_account = bank_accounts[0] if isinstance(bank_accounts, list) and bank_accounts and isinstance(bank_accounts[0], dict) else {}

    full_name = _safe_text(personal.get("full_name") or personal.get("name"))
    first_name = _safe_text(personal.get("first_name"))
    middle_name = _safe_text(personal.get("middle_name"))
    last_name = _safe_text(personal.get("last_name"))

    if full_name and not first_name:
        first_name = full_name.split(" ")[0]
    if full_name and not middle_name and len(full_name.split(" ")) > 2:
        middle_name = " ".join(full_name.split(" ")[1:-1])
    if full_name and not last_name and len(full_name.split(" ")) > 1:
        last_name = full_name.split(" ")[-1]

    gst_value = business.get("gst_number") or business.get("gstin")
    assessment_year = _first_non_empty(tax_preferences.get("assessment_year"), tax_preferences.get("ay"))
    financial_year = _first_non_empty(tax_preferences.get("financial_year"), tax_preferences.get("fy"), tax_preferences.get("tds_year"))
    if _is_empty_field_value(assessment_year) and isinstance(financial_year, str):
        fy_match = re.match(r"^(20\d{2})[-/](\d{2})$", _safe_text(financial_year))
        if fy_match:
            start_year = int(fy_match.group(1)) + 1
            end_year = (int(fy_match.group(2)) + 1) % 100
            assessment_year = f"{start_year}-{end_year:02d}"

    taxes_paid = _first_non_empty(
        tax_preferences.get("taxes_paid"),
        tax_preferences.get("total_taxes_paid"),
        tax_preferences.get("tax_paid"),
    )
    refund_amount = _first_non_empty(
        tax_preferences.get("refund_amount"),
        tax_preferences.get("amount_refund"),
    )
    filed_under_section = _first_non_empty(
        tax_preferences.get("filed_under_section"),
        tax_preferences.get("return_filing_section"),
        tax_preferences.get("filing_section"),
        "139(1)",
    )
    filed_in_response_notice = _first_non_empty(
        tax_preferences.get("notice_section"),
        tax_preferences.get("filed_in_response_to_notice"),
        "Not Applicable",
    )
    nature_of_employment = _first_non_empty(
        tax_preferences.get("nature_of_employment"),
        tax_preferences.get("employment_type"),
        personal.get("occupation"),
        "Private Sector Employee",
    )
    opt_out_new_regime = _normalize_yes_no(
        _first_non_empty(
            tax_preferences.get("opt_out_new_tax_regime"),
            tax_preferences.get("opting_out_115bac"),
            tax_preferences.get("old_regime_opted"),
        ),
        default="No",
    )
    seventh_proviso_filing = _normalize_yes_no(
        _first_non_empty(
            tax_preferences.get("seventh_proviso_filing"),
            tax_preferences.get("seventh_proviso_applicable"),
        ),
        default="No",
    )
    representative_assessee = _normalize_yes_no(
        _first_non_empty(
            tax_preferences.get("representative_assessee"),
            tax_preferences.get("has_representative"),
        ),
        default="No",
    )
    salary_income_pref = _first_non_empty(
        tax_preferences.get("salary_income"),
        tax_preferences.get("income_from_salary"),
        tax_preferences.get("income_salaries"),
    )
    other_income_pref = _first_non_empty(
        tax_preferences.get("income_from_other_sources"),
        tax_preferences.get("other_income"),
        tax_preferences.get("other_sources_income"),
    )
    total_deductions_pref = _first_non_empty(
        tax_preferences.get("total_deductions"),
        tax_preferences.get("deductions_total"),
    )
    total_tax_liability_pref = _first_non_empty(
        tax_preferences.get("total_tax_liability"),
        tax_preferences.get("total_tax_fee_interest"),
    )
    refund_flag = _normalize_yes_no(
        _first_non_empty(
            first_account.get("refund_flag"),
            tax_preferences.get("refund_flag"),
            tax_preferences.get("selected_for_refund"),
        ),
        default="Yes",
    )
    verification_capacity = _first_non_empty(
        tax_preferences.get("verification_capacity"),
        tax_preferences.get("capacity"),
        "Self",
    )

    lookup: dict[str, Any] = {
        "name": full_name,
        "full name": full_name,
        "first name": first_name,
        "middle name": middle_name,
        "last name": last_name,
        "pan": personal.get("pan"),
        "aadhaar": personal.get("aadhaar"),
        "dob": personal.get("dob") or personal.get("date_of_birth"),
        "date of birth": personal.get("dob") or personal.get("date_of_birth"),
        "phone": personal.get("phone") or personal.get("mobile"),
        "mobile": personal.get("mobile") or personal.get("phone"),
        "secondary mobile": personal.get("secondary_phone") or personal.get("alternate_phone"),
        "email": personal.get("email"),
        "secondary email": personal.get("secondary_email") or personal.get("alternate_email"),
        "address": personal.get("address"),
        "address flat": address.get("flat") or address.get("flat_no") or address.get("door_no"),
        "address premises": address.get("premises") or address.get("building") or address.get("village"),
        "address street": address.get("street") or address.get("road") or address.get("post_office"),
        "address city": address.get("city") or address.get("district") or address.get("town"),
        "address state": address.get("state"),
        "address country": address.get("country"),
        "address pin code": address.get("pin_code") or address.get("pincode"),
        "secondary address flat": secondary_address.get("flat") or secondary_address.get("flat_no") or secondary_address.get("door_no"),
        "secondary address premises": secondary_address.get("premises") or secondary_address.get("building") or secondary_address.get("village"),
        "secondary address street": secondary_address.get("street") or secondary_address.get("road") or secondary_address.get("post_office"),
        "secondary address city": secondary_address.get("city") or secondary_address.get("district") or secondary_address.get("town"),
        "secondary address state": secondary_address.get("state"),
        "secondary address country": secondary_address.get("country"),
        "secondary address pin code": secondary_address.get("pin_code") or secondary_address.get("pincode"),
        "business name": business.get("business_name"),
        "entity type": business.get("entity_type"),
        "industry": business.get("industry"),
        "gstin": gst_value,
        "gst number": gst_value,
        "annual turnover": business.get("annual_turnover"),
        "assessment year": assessment_year,
        "financial year": financial_year,
        "filed under section": filed_under_section,
        "filed in response to notice": filed_in_response_notice,
        "nature of employment": nature_of_employment,
        "opting out of new tax regime": opt_out_new_regime,
        "opt out new tax regime": opt_out_new_regime,
        "filing under seventh proviso": seventh_proviso_filing,
        "seventh proviso filing": seventh_proviso_filing,
        "seventh proviso applicable": seventh_proviso_filing,
        "foreign travel expenditure": _first_non_empty(tax_preferences.get("foreign_travel_expenditure"), "0"),
        "electricity expenditure": _first_non_empty(tax_preferences.get("electricity_expenditure"), "0"),
        "other prescribed conditions": _normalize_yes_no(tax_preferences.get("other_prescribed_conditions"), default="No"),
        "representative assessee": representative_assessee,
        "representative name": tax_preferences.get("representative_name"),
        "representative email": tax_preferences.get("representative_email"),
        "representative contact": tax_preferences.get("representative_contact"),
        "verification capacity": verification_capacity,
        "capacity": verification_capacity,
        "today date": datetime.now().date().isoformat(),
        "taxes paid": taxes_paid,
        "refund amount": refund_amount,
        "salary income": salary_income_pref,
        "income from salary": salary_income_pref,
        "income from other sources": other_income_pref,
        "other income": other_income_pref,
        "total deductions": total_deductions_pref,
        "total tax liability": total_tax_liability_pref,
        "selected for refund": refund_flag,
        "refund flag": refund_flag,
    }

    for key, value in personal.items():
        normalized_key = key.replace("_", " ").strip().lower()
        if normalized_key and normalized_key not in lookup:
            lookup[normalized_key] = value

    for key, value in business.items():
        normalized_key = key.replace("_", " ").strip().lower()
        if normalized_key and normalized_key not in lookup:
            lookup[normalized_key] = value

    if first_account:
        lookup["bank account"] = first_account.get("account_number") or first_account.get("number")
        lookup["account number"] = first_account.get("account_number") or first_account.get("number")
        lookup["ifsc"] = first_account.get("ifsc")
        lookup["bank name"] = first_account.get("bank_name")
        lookup["account type"] = _first_non_empty(first_account.get("account_type"), "Savings")
        lookup["selected for refund"] = _normalize_yes_no(first_account.get("refund_flag"), default=refund_flag)

    income_sources = profile_doc.get("income_sources", [])
    if isinstance(income_sources, list):
        total_income = 0.0
        salary_income = 0.0
        other_income = 0.0
        for item in income_sources:
            if isinstance(item, dict):
                try:
                    amount = float(item.get("amount", item.get("value", 0.0)) or 0.0)
                except Exception:
                    continue
                total_income += amount
                source_kind = _normalize_key(
                    _safe_text(item.get("type") or item.get("category") or item.get("source") or item.get("name"))
                )
                if any(token in source_kind for token in ("salary", "pension", "wage", "employment")):
                    salary_income += amount
                else:
                    other_income += amount
        if total_income > 0:
            lookup["total income"] = round(total_income, 2)
        if salary_income > 0:
            if _is_empty_field_value(lookup.get("salary income")):
                lookup["salary income"] = round(salary_income, 2)
            if _is_empty_field_value(lookup.get("income from salary")):
                lookup["income from salary"] = round(salary_income, 2)
        if other_income > 0:
            if _is_empty_field_value(lookup.get("income from other sources")):
                lookup["income from other sources"] = round(other_income, 2)
            if _is_empty_field_value(lookup.get("other income")):
                lookup["other income"] = round(other_income, 2)

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


def _set_nested_dict_path(container: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.split(".") if part]
    if not parts:
        return

    current = container
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        if is_last:
            current[part] = value
            return
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value


def _build_profile_updates_from_fields(fields: list[dict[str, Any]]) -> dict[str, Any]:
    updates: dict[str, Any] = {}

    for field in fields:
        field_id = _safe_text(field.get("field_id"))
        profile_path = ITR1_FIELD_TO_PROFILE_PATH.get(field_id)
        if not profile_path:
            continue

        value = field.get("value")
        if _is_empty_field_value(value):
            continue

        if isinstance(value, str):
            value = value.strip()
        if _is_empty_field_value(value):
            continue

        if isinstance(value, str) and "*" in value and any(token in profile_path for token in ("pan", "aadhaar", "account_number")):
            continue

        if profile_path.startswith("bank_accounts."):
            parts = profile_path.split(".")
            if len(parts) < 3 or not parts[1].isdigit():
                continue
            account_index = int(parts[1])
            account_path = ".".join(parts[2:])
            bank_accounts = updates.setdefault("bank_accounts", [])
            if not isinstance(bank_accounts, list):
                bank_accounts = []
                updates["bank_accounts"] = bank_accounts
            while len(bank_accounts) <= account_index:
                bank_accounts.append({})
            if not isinstance(bank_accounts[account_index], dict):
                bank_accounts[account_index] = {}
            _set_nested_dict_path(bank_accounts[account_index], account_path, value)
            continue

        root, _, nested_path = profile_path.partition(".")
        if not nested_path:
            updates[root] = value
            continue
        root_container = updates.setdefault(root, {})
        if not isinstance(root_container, dict):
            root_container = {}
            updates[root] = root_container
        _set_nested_dict_path(root_container, nested_path, value)

    personal_info = updates.get("personal_info")
    if isinstance(personal_info, dict):
        first_name = _safe_text(personal_info.get("first_name"))
        middle_name = _safe_text(personal_info.get("middle_name"))
        last_name = _safe_text(personal_info.get("last_name"))
        if not _safe_text(personal_info.get("full_name")):
            name_parts = [part for part in [first_name, middle_name, last_name] if part]
            if name_parts:
                personal_info["full_name"] = " ".join(name_parts)

    cleaned_updates: dict[str, Any] = {}
    for key, value in updates.items():
        if isinstance(value, dict) and value:
            cleaned_updates[key] = value
        elif isinstance(value, list):
            non_empty_items = [item for item in value if isinstance(item, dict) and item]
            if non_empty_items:
                cleaned_updates[key] = value
        elif value not in (None, ""):
            cleaned_updates[key] = value

    return cleaned_updates


def _sync_profile_from_report_fields(user_id: str, fields: list[dict[str, Any]]) -> bool:
    profile_updates = _build_profile_updates_from_fields(fields)
    if not profile_updates:
        return False
    update_profile(user_id, profile_updates)
    return True


def _task_report_extract_fields(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_name = _normalize_report_name(payload.get("report_name"))
    normalized_payload = {**payload, "report_name": report_name}
    extracted_fields = _extract_report_fields(normalized_payload)
    filled_entities = _prefill_report_fields_from_profile(user_id, extracted_fields)
    missing_fields = [
        {
            "field_id": field.get("field_id"),
            "field_name": field.get("field_name"),
            "prompt": field.get("prompt") or f"Please provide {field.get('field_name')}",
            "source": "profile_or_manual",
            "section": field.get("section"),
        }
        for field in filled_entities
        if _is_empty_field_value(field.get("value"))
    ]

    return {
        "report_name": report_name,
        "fields": filled_entities,
        "filled_entities": filled_entities,
        "prefill_fields": filled_entities,
        "missing_fields": missing_fields,
        "required_user_inputs": missing_fields,
        "profile_values": _profile_value_map(user_id),
    }


def _task_report_generate(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_name = _normalize_report_name(payload.get("report_name"))
    normalized_payload = {**payload, "report_name": report_name}
    extracted = _extract_report_fields(normalized_payload)
    values = {}
    values.update(_profile_value_map(user_id))
    values.update(_ledger_value_map(user_id))
    missing_fields: list[dict[str, Any]] = []
    filled: list[dict[str, Any]] = []

    for field in extracted:
        field_id = _safe_text(field.get("field_id") or f"A{len(filled) + 1}")
        field_name = _safe_text(field.get("field_name") or "")
        selected_value = field.get("value")
        source = field.get("source")

        if _is_empty_field_value(selected_value):
            selected_value = _resolve_prefill_value(field_id, field_name, values)
            if not _is_empty_field_value(selected_value):
                source = "profile_or_ledger"

        normalized_field = {
            "field_id": field_id,
            "field_name": field_name or f"Field {len(filled) + 1}",
            "value": selected_value,
            "status": "filled",
            "section": field.get("section"),
            "path": field.get("path"),
            "required": field.get("required", True),
            "prompt": field.get("prompt") or f"Please provide {field_name or f'Field {len(filled) + 1}'}",
            "source": source or "manual",
        }

        if _is_empty_field_value(selected_value):
            normalized_field["status"] = "missing"
            missing_fields.append({
                "field_id": normalized_field["field_id"],
                "field_name": normalized_field["field_name"],
                "prompt": normalized_field["prompt"],
                "source": "profile_or_manual",
                "section": normalized_field.get("section"),
            })
        else:
            normalized_field["value"] = selected_value

        filled.append(normalized_field)

    _sync_profile_from_report_fields(user_id, filled)

    prefilled_fields = _prefill_report_fields_from_profile(user_id, filled)

    profile_doc = _profiles_collection().find_one(
        {"user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0},
    ) or {}
    profile_missing_required = _missing_required_profile_fields(_decrypt_profile_doc(profile_doc))

    required_user_inputs: list[dict[str, Any]] = []
    seen_required_ids: set[str] = set()

    for item in missing_fields:
        req_id = _safe_text(item.get("field_id") or item.get("field_name"))
        if req_id and req_id in seen_required_ids:
            continue
        if req_id:
            seen_required_ids.add(req_id)
        required_user_inputs.append(item)

    for field_path in profile_missing_required:
        readable_name = field_path.replace(".", " ").replace("_", " ")
        if field_path in seen_required_ids:
            continue
        seen_required_ids.add(field_path)
        required_user_inputs.append(
            {
                "field_id": field_path,
                "field_name": readable_name,
                "prompt": f"Update profile with {readable_name}",
                "source": "profile_required",
            }
        )

    report_id = payload.get("report_id") or str(uuid4())
    existing_report = _reports_collection().find_one({"report_id": report_id, "user_id": user_id}, {"_id": 0, "created_at": 1}) or {}
    report_doc = {
        "report_id": report_id,
        "user_id": user_id,
        "status": "generated" if not required_user_inputs else "needs_user_input",
        "report_name": report_name,
        "fields": filled,
        "missing_fields": missing_fields,
        "required_user_inputs": required_user_inputs,
        "profile_missing_required": profile_missing_required,
        "created_at": existing_report.get("created_at") or _now_iso(),
        "updated_at": _now_iso(),
        "schema_version": "itr1-v1",
    }
    _reports_collection().update_one({"report_id": report_id}, {"$set": report_doc}, upsert=True)

    return {
        "report_id": report_id,
        "report_name": report_name,
        "status": report_doc["status"],
        "fields": filled,
        "filled_entities": prefilled_fields,
        "prefill_fields": prefilled_fields,
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
    report_name = ITR1_REPORT_NAME
    fields = _extract_report_fields({"report_name": report_name})
    form_fields = _prefill_report_fields_from_profile(user_id, fields)
    missing_fields = [
        {
            "field_id": field.get("field_id"),
            "field_name": field.get("field_name"),
            "prompt": field.get("prompt") or f"Please provide {field.get('field_name')}",
            "source": "profile_or_manual",
            "section": field.get("section"),
        }
        for field in form_fields
        if _is_empty_field_value(field.get("value"))
    ]

    return {
        "report_name": report_name,
        "profile": profile_doc,
        "user": user_doc,
        "fields": form_fields,
        "prefill_fields": form_fields,
        "missing_fields": missing_fields,
        "required_user_inputs": missing_fields,
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

    payload_fields = _coerce_field_list(payload.get("fields"))
    if payload_fields:
        fields = payload_fields

    if not fields and payload.get("report_id"):
        report = _reports_collection().find_one({"report_id": payload["report_id"], "user_id": user_id}, {"_id": 0})
        if report:
            fields = report.get("fields", fields)

    if not fields:
        normalized_payload = {**payload, "report_name": _normalize_report_name(payload.get("report_name"))}
        if payload.get("file_path") and os.path.exists(payload["file_path"]):
            fields = extract_filled_fields_from_pdf(payload["file_path"])
        else:
            fields = _extract_report_fields(normalized_payload)

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

    queued_new = scan_deadlines_once(user_id=user_id, force_queue=True)
    sent_now = dispatch_queued_notifications(limit=50, user_id=user_id)
    still_queued = _get_db()["notifications"].count_documents({"user_id": user_id, "status": "queued"})

    return {
        "saved": True,
        "deadline": doc,
        "notification": {
            "queued_new": queued_new,
            "sent": sent_now,
            "still_queued": still_queued,
        },
    }


def _task_deadline_get(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    sync_summary = _sync_transaction_deadlines(user_id)
    items = list(_deadlines_collection().find({"user_id": user_id}, {"_id": 0}).sort("due_date", 1))

    deadline_ids = [item.get("deadline_id") for item in items if item.get("deadline_id")]
    notification_index: dict[str, dict[str, Any]] = {}
    if deadline_ids:
        notifications = list(
            _get_db()["notifications"].find(
                {
                    "user_id": user_id,
                    "deadline_id": {"$in": deadline_ids},
                },
                {
                    "_id": 0,
                    "deadline_id": 1,
                    "status": 1,
                    "sent_at": 1,
                    "updated_at": 1,
                    "error": 1,
                },
            ).sort("updated_at", -1)
        )

        for n in notifications:
            d_id = n.get("deadline_id")
            if d_id and d_id not in notification_index:
                notification_index[d_id] = n

    for item in items:
        d_id = item.get("deadline_id")
        notif = notification_index.get(d_id)
        meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
        if notif:
            meta["reminder_status"] = notif.get("status")
            meta["reminder_sent_at"] = notif.get("sent_at")
            if notif.get("error"):
                meta["reminder_error"] = notif.get("error")
        item["meta"] = meta

    return {
        "deadlines": items,
        "count": len(items),
        "transaction_deadline_sync": sync_summary,
    }


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

    queued_new = scan_deadlines_once(user_id=user_id, force_queue=True)
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
    response = execute_goal(user_id, message)
    return {"answered": True, "response": response, "in_scope": in_scope}


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
