from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from finpilot.api.deps import fetch_user_transactions
from finpilot.db.mongo import _get_db
from finpilot.utils.profile_security import decrypt_sensitive_value

router = APIRouter(prefix="/reports/financial", tags=["Financial Reports"])


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _fmt_amount(value: Any) -> str:
    return f"{_safe_float(value):.2f}"


def _clean_html_value(value: Any, fallback: str = "N/A") -> str:
    text = _safe_text(value, fallback)
    return html.escape(text)


def _profiles_collection():
    return _get_db()["profiles"]


def _load_profile_doc(user_id: str) -> dict[str, Any]:
    profile_doc = _profiles_collection().find_one(
        {"user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0},
    ) or {}

    personal = profile_doc.get("personal_info")
    if isinstance(personal, dict):
        for key in ("pan", "aadhaar"):
            if key in personal:
                personal[key] = decrypt_sensitive_value(personal.get(key))

    return profile_doc


def _extract_address(profile_doc: dict[str, Any]) -> dict[str, str]:
    personal = profile_doc.get("personal_info") if isinstance(profile_doc.get("personal_info"), dict) else {}
    address = personal.get("address") if isinstance(personal, dict) else {}

    if isinstance(address, dict):
        flat = _safe_text(
            address.get("flat")
            or address.get("house_no")
            or address.get("house_number")
            or address.get("address_flat")
        )
        building = _safe_text(
            address.get("building")
            or address.get("street")
            or address.get("address_building")
        )
        area = _safe_text(address.get("area") or address.get("locality") or address.get("address_area"))
        district = _safe_text(address.get("district") or address.get("city") or address.get("address_district"))
        state = _safe_text(address.get("state") or address.get("address_state"))
        pin = _safe_text(address.get("pin_code") or address.get("pincode") or address.get("address_pin"))
        country = _safe_text(address.get("country") or address.get("address_country"), "India")
        parts = [part for part in [flat, building, area, district, state, pin] if part]
        full_address = ", ".join(parts) if parts else ""
    else:
        full_address = _safe_text(address or personal.get("address_line") or personal.get("full_address"))
        flat = _safe_text(personal.get("address_flat"))
        building = _safe_text(personal.get("address_building"))
        area = _safe_text(personal.get("address_area"))
        district = _safe_text(personal.get("address_district"))
        state = _safe_text(personal.get("address_state"))
        pin = _safe_text(personal.get("address_pin") or personal.get("pin_code"))
        country = _safe_text(personal.get("address_country"), "India")

    return {
        "address": full_address or "N/A",
        "address_flat": flat or "N/A",
        "address_building": building or "N/A",
        "address_area": area or "N/A",
        "address_district": district or "N/A",
        "address_state": state or "N/A",
        "address_pin": pin or "N/A",
        "address_country": country or "India",
    }


def _extract_bank_accounts(profile_doc: dict[str, Any]) -> list[dict[str, str]]:
    bank_accounts = profile_doc.get("bank_accounts", [])
    normalized: list[dict[str, str]] = []

    if not isinstance(bank_accounts, list):
        bank_accounts = []

    for item in bank_accounts[:2]:
        if isinstance(item, dict):
            normalized.append(
                {
                    "bank_name": _safe_text(item.get("bank_name") or item.get("name") or item.get("bank"), "N/A"),
                    "account_number": _safe_text(item.get("account_number") or item.get("number") or item.get("account"), "N/A"),
                    "type": _safe_text(item.get("account_type") or item.get("type") or item.get("bank_type"), "N/A"),
                    "ifsc": _safe_text(item.get("ifsc") or item.get("ifsc_code"), "N/A"),
                }
            )
        else:
            normalized.append({"bank_name": _safe_text(item, "N/A"), "account_number": "N/A", "type": "N/A", "ifsc": "N/A"})

    while len(normalized) < 2:
        normalized.append({"bank_name": "N/A", "account_number": "N/A", "type": "N/A", "ifsc": "N/A"})

    return normalized


INCOME_KEYWORDS = {
    "salary": {"salary", "payroll", "wage", "wages", "stipend", "compensation"},
    "house_property": {"rent", "rental", "house property", "lease", "property rent"},
    "interest": {"interest", "fd interest", "bank interest", "savings interest", "deposit interest"},
    "dividend": {"dividend"},
}

DEDUCTION_KEYWORDS = {
    "deductions_80c": {"epf", "ppf", "lic", "elss", "nps", "tax saver", "insurance premium", "life insurance", "ulip"},
    "deductions_80ccc": set(),
    "deductions_80ccd": set(),
    "deductions_80d": {"health insurance", "medical insurance", "hospital", "medical", "pharmacy", "diagnostic"},
    "deductions_80dd": {"disabled dependent", "dependent disability"},
    "deductions_80ddb": {"medical treatment", "critical illness", "dialysis"},
    "deductions_80e": {"education loan", "student loan", "tuition", "education fee"},
    "deductions_80g": {"donation", "charity", "charitable"},
    "deductions_80gg": {"rent paid", "hra", "house rent"},
    "deductions_80u": {"disability", "person with disability"},
    "deductions_80ia": set(),
}

TDS_KEYWORDS = {"tds", "tax deducted at source", "tds credit"}


def _transaction_text(txn: Any) -> str:
    parts = [
        getattr(txn, "party", ""),
        getattr(txn, "category", ""),
        getattr(txn, "sub_category", ""),
        getattr(txn, "raw_text", ""),
    ]
    return _safe_text(" ".join(str(part) for part in parts if part))


def _contains_any(text: str, keywords: set[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _classify_income_buckets(txns: list[Any]) -> dict[str, Any]:
    salary_income = 0.0
    house_property_income = 0.0
    interest_income = 0.0
    dividend_income = 0.0
    other_income = 0.0
    tds_paid = 0.0
    deduction_totals: dict[str, float] = {
        "deductions_80c": 0.0,
        "deductions_80ccc": 0.0,
        "deductions_80ccd": 0.0,
        "deductions_80d": 0.0,
        "deductions_80dd": 0.0,
        "deductions_80ddb": 0.0,
        "deductions_80e": 0.0,
        "deductions_80g": 0.0,
        "deductions_80gg": 0.0,
        "deductions_80u": 0.0,
        "deductions_80ia": 0.0,
    }
    advance_tax_paid = 0.0
    self_assessment_tax = 0.0
    tds_txn = None
    income_category_hits: dict[str, float] = {"salary": 0.0, "house_property": 0.0, "interest": 0.0, "dividend": 0.0, "other": 0.0}

    for txn in txns:
        amount = _safe_float(getattr(txn, "amount", 0.0))
        txn_type = _safe_text(getattr(txn, "type", "")).lower()
        text = _transaction_text(txn)
        category = _safe_text(getattr(txn, "category", "")).lower()

        if txn_type == "credit":
            if _contains_any(text, INCOME_KEYWORDS["salary"]) or category in {"salary", "payroll"}:
                salary_income += amount
                income_category_hits["salary"] += amount
            elif _contains_any(text, INCOME_KEYWORDS["house_property"]) or category in {"house property", "rental income", "rent"}:
                house_property_income += amount
                income_category_hits["house_property"] += amount
            elif _contains_any(text, INCOME_KEYWORDS["interest"]):
                interest_income += amount
                income_category_hits["interest"] += amount
            elif _contains_any(text, INCOME_KEYWORDS["dividend"]):
                dividend_income += amount
                income_category_hits["dividend"] += amount
            else:
                other_income += amount
                income_category_hits["other"] += amount

        if txn_type == "debit":
            if _contains_any(text, TDS_KEYWORDS) or category in {"tds", "tds_credit"}:
                tds_paid += amount
                if tds_txn is None:
                    tds_txn = txn
            if _contains_any(text, {"advance tax"}):
                advance_tax_paid += amount
            if _contains_any(text, {"self assessment tax", "self-assessment tax"}):
                self_assessment_tax += amount
            for section_key, keywords in DEDUCTION_KEYWORDS.items():
                if _contains_any(text, keywords) or section_key.replace("deductions_", "") in category:
                    deduction_totals[section_key] += amount
                    break

    return {
        "salary_income": salary_income,
        "house_property_income": house_property_income,
        "interest_income": interest_income,
        "dividend_income": dividend_income,
        "other_income": other_income,
        "tds_paid": tds_paid,
        "deduction_totals": deduction_totals,
        "advance_tax_paid": advance_tax_paid,
        "self_assessment_tax": self_assessment_tax,
        "tds_txn": tds_txn,
        "income_category_hits": income_category_hits,
    }


def _build_report_data(user_id: str) -> dict[str, Any]:
    txns = fetch_user_transactions(user_id)
    profile_doc = _load_profile_doc(user_id)

    personal = profile_doc.get("personal_info") if isinstance(profile_doc.get("personal_info"), dict) else {}
    business = profile_doc.get("business_info") if isinstance(profile_doc.get("business_info"), dict) else {}
    tax_preferences = profile_doc.get("tax_preferences") if isinstance(profile_doc.get("tax_preferences"), dict) else {}
    address = _extract_address(profile_doc)
    bank_accounts = _extract_bank_accounts(profile_doc)
    txn_summary = _classify_income_buckets(txns)

    full_name = _safe_text(
        personal.get("full_name") or personal.get("name") or business.get("business_name") or user_id,
        "Financial Report User",
    )
    name_parts = [part for part in full_name.split() if part]
    first_name = _safe_text(personal.get("first_name") or (name_parts[0] if name_parts else full_name), full_name)
    middle_name = _safe_text(personal.get("middle_name"))
    last_name = _safe_text(personal.get("last_name") or (name_parts[-1] if len(name_parts) > 1 else ""), full_name)

    email = _safe_text(personal.get("email") or personal.get("primary_email") or "")
    phone = _safe_text(personal.get("phone") or personal.get("mobile") or personal.get("contact_number") or "")
    dob = _safe_text(personal.get("dob") or personal.get("date_of_birth") or "")
    pan = _safe_text(personal.get("pan") or "")
    aadhaar = _safe_text(personal.get("aadhaar") or personal.get("aadhaar_number") or "")
    father_name = _safe_text(personal.get("father_name") or "")
    residence_status = _safe_text(tax_preferences.get("residence_status") or "Resident", "Resident")
    assessment_year = _safe_text(tax_preferences.get("assessment_year") or "2026-27", "2026-27")
    financial_year = _safe_text(tax_preferences.get("financial_year") or "2025-26", "2025-26")

    salary_income = txn_summary["salary_income"]
    house_property_income = txn_summary["house_property_income"]
    interest_income = txn_summary["interest_income"]
    dividend_income = txn_summary["dividend_income"]
    other_income = txn_summary["other_income"]
    gross_total_income = max(0.0, salary_income + house_property_income + interest_income + dividend_income + other_income)

    profile_deduction_80c = _safe_float(tax_preferences.get("deductions_80c"))
    profile_deduction_80d = _safe_float(tax_preferences.get("deductions_80d"))
    profile_deduction_80dd = _safe_float(tax_preferences.get("deductions_80dd"))
    profile_deduction_80ddb = _safe_float(tax_preferences.get("deductions_80ddb"))
    profile_deduction_80e = _safe_float(tax_preferences.get("deductions_80e"))
    profile_deduction_80g = _safe_float(tax_preferences.get("deductions_80g"))
    profile_deduction_80u = _safe_float(tax_preferences.get("deductions_80u"))
    profile_deduction_80gg = _safe_float(tax_preferences.get("deductions_80gg"))
    profile_deduction_80ia = _safe_float(tax_preferences.get("deductions_80ia"))

    deduction_totals = txn_summary["deduction_totals"]
    deduction_80c = max(profile_deduction_80c, deduction_totals["deductions_80c"])
    deduction_80d = max(profile_deduction_80d, deduction_totals["deductions_80d"])
    deduction_80dd = max(profile_deduction_80dd, deduction_totals["deductions_80dd"])
    deduction_80ddb = max(profile_deduction_80ddb, deduction_totals["deductions_80dd"])
    deduction_80e = max(profile_deduction_80e, deduction_totals["deductions_80e"])
    deduction_80g = max(profile_deduction_80g, deduction_totals["deductions_80g"])
    deduction_80u = max(profile_deduction_80u, deduction_totals["deductions_80u"])
    deduction_80gg = max(profile_deduction_80gg, deduction_totals["deductions_80gg"])
    deduction_80ia = max(profile_deduction_80ia, deduction_totals.get("deductions_80ia", 0.0))

    standard_deduction = _safe_float(tax_preferences.get("standard_deduction") or 50000.0)
    total_deductions = (
        deduction_80c
        + deduction_80d
        + deduction_80dd
        + deduction_80ddb
        + deduction_80e
        + deduction_80g
        + deduction_80u
        + deduction_80gg
        + deduction_80ia
    )
    if total_deductions <= 0:
        total_deductions = standard_deduction
        deduction_80c = max(deduction_80c, standard_deduction)

    taxable_income = max(0.0, gross_total_income - total_deductions)
    tax_payable = taxable_income * 0.10 if taxable_income > 300000 else 0.0
    health_cess = tax_payable * 0.04
    interest_234a = _safe_float(tax_preferences.get("interest_234a"))
    interest_234b = _safe_float(tax_preferences.get("interest_234b"))
    interest_234c = _safe_float(tax_preferences.get("interest_234c"))
    fee_234f = _safe_float(tax_preferences.get("fee_234f"))
    total_tax_liability = tax_payable + health_cess + interest_234a + interest_234b + interest_234c + fee_234f
    tds_paid = txn_summary["tds_paid"]
    total_taxes_paid = tds_paid + txn_summary["advance_tax_paid"] + txn_summary["self_assessment_tax"]
    refund_amount = max(0.0, total_taxes_paid - total_tax_liability)

    deduction_rate = (total_deductions / gross_total_income * 100.0) if gross_total_income else 0.0
    effective_tax_rate = (total_tax_liability / taxable_income * 100.0) if taxable_income else 0.0

    report_date = datetime.now().strftime("%Y-%m-%d")
    report_place = _safe_text(
        personal.get("city") or personal.get("location") or address["address_district"] or address["address_state"],
        "N/A",
    )
    tds_txn = txn_summary["tds_txn"]

    income_components = [
        ("Salary", salary_income),
        ("House Property", house_property_income),
        ("Interest", interest_income),
        ("Dividends", dividend_income),
        ("Other Sources", other_income),
    ]
    positive_components = [f"{name}: {_fmt_amount(amount)}" for name, amount in income_components if amount > 0]
    other_sources_description = "; ".join(positive_components[1:]) if len(positive_components) > 1 else "Other credited income from bookkeeping transactions"
    if not other_sources_description:
        other_sources_description = "Other credited income from bookkeeping transactions"

    insights = [
        ("Income Mix", f"The report consolidates {len(txns)} bookkeeping transactions from MongoDB."),
        ("Profile Coverage", f"Prepared using profile data for {full_name} and linked bank details."),
        ("Income Breakdown", f"Salary: {_fmt_amount(salary_income)} | House Property: {_fmt_amount(house_property_income)} | Other Sources: {_fmt_amount(other_income + interest_income + dividend_income)}."),
        ("Tax Position", f"Estimated taxable income is {_fmt_amount(taxable_income)} after deductions of {_fmt_amount(total_deductions)}."),
    ]

    missing_items: list[str] = []
    if not pan:
        missing_items.append("PAN")
    if not phone:
        missing_items.append("contact number")
    if not email:
        missing_items.append("email")
    if not bank_accounts or all(account["bank_name"] == "N/A" for account in bank_accounts):
        missing_items.append("bank account details")

    recommendations = [
        "Reconcile salary and other credit transactions against source statements before filing.",
        "Validate deductions with supporting documents and update the profile where details are missing.",
        "Match TDS entries with Form 26AS or AIS before using this report for filing.",
        "Review high-value credits and uncategorized entries to improve classification accuracy.",
    ]
    if missing_items:
        recommendations.insert(0, f"Complete the following profile details: {', '.join(missing_items)}.")

    bank_1 = bank_accounts[0]
    bank_2 = bank_accounts[1]

    return {
        "status": "ok",
        "user_id": user_id,
        "transactions_count": len(txns),
        "gross_income": round(gross_total_income, 2),
        "total_deductions": round(total_deductions, 2),
        "taxable_income": round(taxable_income, 2),
        "tds_paid": round(tds_paid, 2),
        "report_data": {
            "client_name": full_name,
            "pan": pan or "N/A",
            "assessment_year": assessment_year,
            "financial_year": financial_year,
            "phone": phone or "N/A",
            "phone_secondary": _safe_text(personal.get("phone_secondary") or personal.get("alternate_phone"), "N/A"),
            "email": email or "N/A",
            "email_secondary": _safe_text(personal.get("email_secondary") or personal.get("alternate_email"), "N/A"),
            "address": address["address"],
            "report_date": report_date,
            "report_place": report_place,
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "father_name": father_name or "N/A",
            "dob": dob or "N/A",
            "aadhaar": aadhaar or "N/A",
            "mobile_primary": phone or "N/A",
            "mobile_secondary": _safe_text(personal.get("mobile_secondary") or personal.get("secondary_phone"), "N/A"),
            "email_primary": email or "N/A",
            "email_secondary": _safe_text(personal.get("email_secondary") or personal.get("alternate_email"), "N/A"),
            "address_flat": address["address_flat"],
            "address_building": address["address_building"],
            "address_area": address["address_area"],
            "address_district": address["address_district"],
            "address_state": address["address_state"],
            "address_pin": address["address_pin"],
            "address_country": address["address_country"],
            "residence_status": residence_status,
            "salary_gross": _fmt_amount(salary_income),
            "perquisites_value": _fmt_amount(personal.get("perquisites_value") or 0.0),
            "profit_in_lieu": _fmt_amount(personal.get("profit_in_lieu") or 0.0),
            "income_salaries": _fmt_amount(salary_income),
            "property_address": _safe_text(personal.get("property_address") or "N/A", "N/A"),
            "property_status": _safe_text(personal.get("property_status") or ("Self-Occupied" if house_property_income == 0 else "Let Out"), "Self-Occupied"),
            "rent_receivable": _fmt_amount(personal.get("rent_receivable") or house_property_income),
            "municipal_tax": _fmt_amount(personal.get("municipal_tax") or 0.0),
            "annual_value": _fmt_amount(personal.get("annual_value") or house_property_income),
            "income_house_prop": _fmt_amount(house_property_income),
            "other_sources_description": _safe_text(personal.get("other_sources_description") or other_sources_description, other_sources_description),
            "income_other_sources": _fmt_amount(other_income + interest_income + dividend_income),
            "gross_total_income": _fmt_amount(gross_total_income),
            "deductions_80c": _fmt_amount(deduction_80c),
            "deductions_80ccc": _fmt_amount(tax_preferences.get("deductions_80ccc") or 0.0),
            "deductions_80ccd": _fmt_amount(tax_preferences.get("deductions_80ccd") or 0.0),
            "deductions_80d": _fmt_amount(deduction_80d),
            "deductions_80dd": _fmt_amount(deduction_80dd),
            "deductions_80ddb": _fmt_amount(deduction_80ddb),
            "deductions_80e": _fmt_amount(deduction_80e),
            "deductions_80g": _fmt_amount(deduction_80g),
            "deductions_80gg": _fmt_amount(deduction_80gg),
            "deductions_80u": _fmt_amount(deduction_80u),
            "deductions_80ia": _fmt_amount(deduction_80ia),
            "total_deductions": _fmt_amount(total_deductions),
            "taxable_income": _fmt_amount(taxable_income),
            "tax_payable": _fmt_amount(tax_payable),
            "health_cess": _fmt_amount(health_cess),
            "interest_234a": _fmt_amount(interest_234a),
            "interest_234b": _fmt_amount(interest_234b),
            "interest_234c": _fmt_amount(interest_234c),
            "fee_234f": _fmt_amount(fee_234f),
            "total_tax_liability": _fmt_amount(total_tax_liability),
            "total_taxes_paid": _fmt_amount(total_taxes_paid),
            "refund_amount": _fmt_amount(refund_amount),
            "bank_name_1": bank_1["bank_name"],
            "bank_ifsc_1": bank_1["ifsc"],
            "bank_account_1": bank_1["account_number"],
            "bank_type_1": bank_1["type"],
            "bank_name_2": bank_2["bank_name"],
            "bank_ifsc_2": bank_2["ifsc"],
            "bank_account_2": bank_2["account_number"],
            "bank_type_2": bank_2["type"],
            "tds_deductor_name": _safe_text(getattr(tds_txn, "party", "") if tds_txn else personal.get("tds_deductor_name") or "N/A", "N/A"),
            "tds_tan": _safe_text(personal.get("tds_tan") or "N/A", "N/A"),
            "tds_section": _safe_text(getattr(tds_txn, "category", "") if tds_txn else personal.get("tds_section") or "N/A", "N/A"),
            "tds_gross_payment": _fmt_amount(salary_income if salary_income > 0 else gross_total_income),
            "tds_period_from": _safe_text(personal.get("tds_period_from") or "N/A", "N/A"),
            "tds_period_to": _safe_text(personal.get("tds_period_to") or "N/A", "N/A"),
            "tds_deducted": _fmt_amount(tds_paid),
            "tds_credit": _fmt_amount(tds_paid),
            "assessee_name": full_name,
            "capacity": _safe_text(business.get("entity_type") or "Individual", "Individual"),
            "verification_date": report_date,
            "verification_place": report_place,
            "deduction_rate": f"{deduction_rate:.2f}",
            "effective_tax_rate": f"{effective_tax_rate:.2f}",
            "insight_title_1": insights[0][0],
            "insight_detail_1": insights[0][1],
            "insight_title_2": insights[1][0],
            "insight_detail_2": insights[1][1],
            "insight_title_3": insights[2][0],
            "insight_detail_3": insights[2][1],
            "insight_title_4": insights[3][0],
            "insight_detail_4": insights[3][1],
            "recommendation_1": recommendations[0],
            "recommendation_2": recommendations[1] if len(recommendations) > 1 else recommendations[0],
            "recommendation_3": recommendations[2] if len(recommendations) > 2 else recommendations[0],
            "recommendation_4": recommendations[3] if len(recommendations) > 3 else recommendations[0],
            "ca_name": "CA",
            "ca_regn_no": "N/A",
            "ca_membership_no": "N/A",
            "ca_email": "N/A",
            "ca_phone": "N/A",
            "ca_firm_name": "Professional Tax & Financial Services",
            "interest_savings": _fmt_amount(interest_income),
            "interest_fixed_deposits": _fmt_amount(interest_income),
            "dividend_mutual_funds": _fmt_amount(dividend_income),
            "interest_on_capital": _fmt_amount(0.0),
            "repairs_maintenance": _fmt_amount(0.0),
            "insurance_premium": _fmt_amount(deduction_80d),
            "other_income_description": _safe_text(personal.get("other_income_description") or other_sources_description, other_sources_description),
            "other_income_amount": _fmt_amount(other_income + interest_income + dividend_income),
            "advance_tax_paid": _fmt_amount(txn_summary["advance_tax_paid"]),
            "self_assessment_tax": _fmt_amount(txn_summary["self_assessment_tax"]),
        },
    }
@router.post("/generate/{user_id}")
def generate_financial_report_route(user_id: str):
    data = _build_report_data(user_id)
    return {
        "status": "ok",
        "message": "Financial report data generated",
        "user_id": user_id,
        "transactions_count": data["transactions_count"],
        "gross_income": data["gross_income"],
        "total_deductions": data["total_deductions"],
        "taxable_income": data["taxable_income"],
        "tds_paid": data["tds_paid"],
    }


@router.get("/download/{user_id}")
def download_financial_report_route(user_id: str, format: str = Query("html")):
    data = _build_report_data(user_id)
    if format.lower() != "html":
        return {
            "status": "error",
            "message": "Only html format is supported",
            "user_id": user_id,
        }

    backend_root = Path(__file__).resolve().parents[3]
    template_candidates = [
        backend_root / "FINANCIAL-REPORT-TEMPLATE.html",
        backend_root / "templates" / "FINANCIAL-REPORT-TEMPLATE.html",
    ]

    template_path = next((p for p in template_candidates if p.exists()), None)
    if template_path is None:
        return {
            "status": "error",
            "message": "Financial report template not found",
            "user_id": user_id,
        }

    html_content = template_path.read_text(encoding="utf-8")
    for key, value in data["report_data"].items():
        html_content = html_content.replace(f"{{{{{key}}}}}", _clean_html_value(value, "N/A"))

    html_content = re.sub(r"\{\{\s*[^{}]+\s*\}\}", "N/A", html_content)

    output_dir = Path(__file__).resolve().parents[4] / "data" / "generated" / "financial_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"Financial-Report-{user_id}.html"
    output_path.write_text(html_content, encoding="utf-8")

    return FileResponse(
        path=str(output_path),
        media_type="text/html",
        filename=output_path.name,
    )
