from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from finpilot.api.deps import fetch_user_transactions

router = APIRouter(prefix="/reports/financial", tags=["Financial Reports"])


def _build_report_data(user_id: str) -> dict:
    txns = fetch_user_transactions(user_id)

    salary_income = sum(
        float(t.amount)
        for t in txns
        if str(getattr(t, "category", "")).lower() == "salary"
    )

    other_income = sum(
        float(t.amount)
        for t in txns
        if str(getattr(t, "type", "")).lower() == "credit"
        and str(getattr(t, "category", "")).lower() != "salary"
    )

    tds_paid = sum(
        float(t.amount)
        for t in txns
        if str(getattr(t, "category", "")).lower() in {"tds", "tds_credit"}
    )

    total_deductions = 50000.0
    gross_total_income = max(0.0, salary_income + other_income)
    taxable_income = max(0.0, gross_total_income - total_deductions)

    tax_payable = 0.0
    if taxable_income > 300000:
        tax_payable = taxable_income * 0.10

    health_cess = tax_payable * 0.04
    total_tax_liability = tax_payable + health_cess
    refund_amount = max(0.0, tds_paid - total_tax_liability)

    deduction_rate = (total_deductions / gross_total_income * 100.0) if gross_total_income else 0.0
    effective_tax_rate = (total_tax_liability / taxable_income * 100.0) if taxable_income else 0.0

    return {
        "status": "ok",
        "user_id": user_id,
        "transactions_count": len(txns),
        "gross_income": round(gross_total_income, 2),
        "total_deductions": round(total_deductions, 2),
        "taxable_income": round(taxable_income, 2),
        "tds_paid": round(tds_paid, 2),
        "report_data": {
            "client_name": "Financial Report User",
            "pan": "",
            "assessment_year": "2026-27",
            "financial_year": "2025-26",
            "phone": "",
            "phone_secondary": "",
            "email": "",
            "email_secondary": "",
            "address": "",
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "report_place": "",
            "first_name": "",
            "middle_name": "",
            "last_name": "",
            "father_name": "",
            "dob": "",
            "aadhaar": "",
            "mobile_primary": "",
            "mobile_secondary": "",
            "email_primary": "",
            "email_secondary": "",
            "address_flat": "",
            "address_building": "",
            "address_area": "",
            "address_district": "",
            "address_state": "",
            "address_pin": "",
            "address_country": "India",
            "residence_status": "Resident",
            "salary_gross": f"{salary_income:.2f}",
            "perquisites_value": "0.00",
            "profit_in_lieu": "0.00",
            "income_salaries": f"{salary_income:.2f}",
            "property_address": "",
            "property_status": "",
            "rent_receivable": "0.00",
            "municipal_tax": "0.00",
            "annual_value": "0.00",
            "income_house_prop": "0.00",
            "other_sources_description": "Other credited income",
            "income_other_sources": f"{other_income:.2f}",
            "gross_total_income": f"{gross_total_income:.2f}",
            "deductions_80c": "50000.00",
            "deductions_80ccc": "0.00",
            "deductions_80ccd": "0.00",
            "deductions_80d": "0.00",
            "deductions_80dd": "0.00",
            "deductions_80ddb": "0.00",
            "deductions_80e": "0.00",
            "deductions_80g": "0.00",
            "deductions_80gg": "0.00",
            "deductions_80u": "0.00",
            "deductions_80ia": "0.00",
            "total_deductions": f"{total_deductions:.2f}",
            "taxable_income": f"{taxable_income:.2f}",
            "tax_payable": f"{tax_payable:.2f}",
            "health_cess": f"{health_cess:.2f}",
            "interest_234a": "0.00",
            "interest_234b": "0.00",
            "interest_234c": "0.00",
            "fee_234f": "0.00",
            "total_tax_liability": f"{total_tax_liability:.2f}",
            "total_taxes_paid": f"{tds_paid:.2f}",
            "refund_amount": f"{refund_amount:.2f}",
            "bank_name_1": "",
            "bank_ifsc_1": "",
            "bank_account_1": "",
            "bank_type_1": "",
            "bank_name_2": "",
            "bank_ifsc_2": "",
            "bank_account_2": "",
            "bank_type_2": "",
            "tds_deductor_name": "",
            "tds_tan": "",
            "tds_section": "",
            "tds_gross_payment": f"{salary_income:.2f}",
            "tds_period_from": "",
            "tds_period_to": "",
            "tds_deducted": f"{tds_paid:.2f}",
            "tds_credit": f"{tds_paid:.2f}",
            "assessee_name": "",
            "capacity": "Individual",
            "verification_date": datetime.now().strftime("%Y-%m-%d"),
            "verification_place": "",
            "deduction_rate": f"{deduction_rate:.2f}",
            "effective_tax_rate": f"{effective_tax_rate:.2f}",
            "insight_title_1": "Income Mix",
            "insight_detail_1": "Salary and other credits are consolidated from ingested transactions.",
            "insight_title_2": "Deduction Coverage",
            "insight_detail_2": "Standard deduction applied for baseline tax computation.",
            "insight_title_3": "Tax Liability",
            "insight_detail_3": "Estimated tax and cess are computed from taxable income.",
            "insight_title_4": "Refund Position",
            "insight_detail_4": "Refund reflects difference between TDS paid and estimated liability.",
            "recommendation_1": "Capture PAN, contact, and bank details to complete the final filing packet.",
            "recommendation_2": "Review deduction sections with proof documents before final submission.",
            "recommendation_3": "Validate TDS with Form 26AS and AIS for accuracy.",
            "recommendation_4": "Reconcile high-value credits with source documents.",
            "ca_name": "",
            "ca_regn_no": "",
            "ca_membership_no": "",
            "ca_email": "",
            "ca_phone": "",
            "ca_firm_name": "",
            "interest_savings": "0.00",
            "interest_fixed_deposits": "0.00",
            "dividend_mutual_funds": "0.00",
            "interest_on_capital": "0.00",
            "repairs_maintenance": "0.00",
            "insurance_premium": "0.00",
            "other_income_description": "",
            "other_income_amount": f"{other_income:.2f}",
            "advance_tax_paid": "0.00",
            "self_assessment_tax": "0.00",
        },
    }


@router.post("/generate/{user_id}")
def generate_financial_report_route(user_id: str):
    data = _build_report_data(user_id)
    if data["transactions_count"] == 0:
        return {
            "status": "error",
            "message": "No transactions found. Ingest data first.",
            "user_id": user_id,
        }
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
    if data["transactions_count"] == 0:
        return {
            "status": "error",
            "message": "No transaction data available for report generation",
            "user_id": user_id,
        }

    if format.lower() != "html":
        return {
            "status": "error",
            "message": "Only html format is supported",
            "user_id": user_id,
        }

    template_candidates = [
        Path(__file__).resolve().parents[4] / "FINANCIAL-REPORT-TEMPLATE.html",
        Path(__file__).resolve().parents[3] / "FINANCIAL-REPORT-TEMPLATE.html",
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
        html_content = html_content.replace(f"{{{{{key}}}}}", str(value))

    # Keep template reusable: unresolved placeholders are blanked.
    html_content = re.sub(r"\{\{\s*[^{}]+\s*\}\}", "", html_content)

    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f"attachment; filename=Financial-Report-{user_id}.html"},
    )
