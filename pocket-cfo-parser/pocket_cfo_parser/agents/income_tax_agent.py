"""
Income Tax Agent

Estimates taxable income, applies common deductions, and computes tax liability.
"""

from collections import defaultdict
from datetime import datetime
from pocket_cfo_parser.models.transaction import Transaction
from pocket_cfo_parser.agents.financial_statements_agent import get_financial_statements


def _round(value: float) -> float:
    return round(value or 0.0, 2)


def calculate_tax_liability(taxable_income: float) -> dict:
    slabs = [
        (250000, 0.0),
        (500000, 0.05),
        (750000, 0.10),
        (1000000, 0.15),
        (1250000, 0.20),
        (1500000, 0.25),
        (float('inf'), 0.30)
    ]
    remaining = taxable_income
    previous_limit = 0.0
    tax = 0.0
    slab_breakdown = []

    for limit, rate in slabs:
        if remaining <= 0:
            break
        taxable_at_rate = min(remaining, limit - previous_limit)
        slab_tax = taxable_at_rate * rate
        if taxable_at_rate > 0:
            slab_breakdown.append({
                "taxable_amount": _round(taxable_at_rate),
                "rate": rate * 100,
                "tax": _round(slab_tax)
            })
        tax += slab_tax
        remaining -= taxable_at_rate
        previous_limit = limit

    cess = tax * 0.04
    total_tax = tax + cess

    return {
        "tax_before_cess": _round(tax),
        "health_and_education_cess": _round(cess),
        "total_tax_liability": _round(total_tax),
        "effective_rate_percent": _round((total_tax / taxable_income) * 100 if taxable_income > 0 else 0.0),
        "slab_breakdown": slab_breakdown
    }


def estimate_deductions(transactions: list[Transaction]) -> dict:
    category_totals = defaultdict(float)
    for txn in transactions:
        if txn.type == "debit":
            category = (txn.category or "Uncategorized").lower()
            if "investment" in category or "mutual" in category or "insurance" in category:
                category_totals["80C"] += txn.amount
            if "health" in category or "medical" in category or "insurance" in category:
                category_totals["80D"] += txn.amount
            if "education" in category or "school" in category or "tuition" in category:
                category_totals["80E"] += txn.amount

    deductions = {
        "80C": min(category_totals.get("80C", 0.0), 150000.0),
        "80D": min(category_totals.get("80D", 0.0), 25000.0),
        "80E": min(category_totals.get("80E", 0.0), 100000.0),
        "standard_deduction": 50000.0
    }
    deductions["total_deductions"] = _round(sum(deductions.values()))
    deductions["notes"] = [
        "Standard deduction is assumed if salary or personal credit exists.",
        "Deductions are estimated from transaction categories and should be verified with actual supporting documents."
    ]
    return deductions


def calculate_taxable_income(transactions: list[Transaction], deductions: dict | None = None) -> dict:
    statements = get_financial_statements(transactions)
    gross_business_profit = statements["profit_and_loss"]["net_profit"]
    personal_income = sum(t.amount for t in transactions if t.type == "credit" and getattr(t, "business_nature", "business") == "personal")
    gross_total_income = gross_business_profit + personal_income

    deductions = deductions or estimate_deductions(transactions)
    taxable_income = max(gross_total_income - deductions.get("total_deductions", 0.0), 0.0)

    return {
        "gross_business_profit": _round(gross_business_profit),
        "personal_income": _round(personal_income),
        "gross_total_income": _round(gross_total_income),
        "deductions": deductions,
        "taxable_income": _round(taxable_income)
    }


def get_income_tax_summary(transactions: list[Transaction]) -> dict:
    taxable = calculate_taxable_income(transactions)
    tax_liability = calculate_tax_liability(taxable["taxable_income"])

    return {
        "report_type": "Income Tax Estimate",
        "generated_at": datetime.now().isoformat(),
        "taxable_income_summary": taxable,
        "tax_liability": tax_liability,
        "tax_planning_advice": [
            "Review eligible 80C and 80D investments before filing.",
            "Separate personal and business expenses clearly for accurate computation.",
            "Retain invoices and proofs for healthcare, education, and insurance deductions."
        ]
    }
