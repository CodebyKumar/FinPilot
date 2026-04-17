"""
Tests for CA-focused agents: financial statements, income tax, reconciliation, and audit.
"""

from datetime import datetime
from pocket_cfo_parser.models.transaction import Transaction
from pocket_cfo_parser.agents.financial_statements_agent import get_financial_statements
from pocket_cfo_parser.agents.income_tax_agent import get_income_tax_summary
from pocket_cfo_parser.agents.reconciliation_agent import get_reconciliation_report
from pocket_cfo_parser.agents.audit_agent import get_audit_report


def make_transaction(amount, txn_type, party, date, category, business_nature, gst_rate=18.0, itc_eligible=False, gst_amount=None, itc_amount=0.0):
    txn = Transaction(
        amount=amount,
        type=txn_type,
        party=party,
        date=date,
        source="sms",
        raw_text=f"{party} {amount}",
        category=category,
        business_nature=business_nature,
        gst_rate=gst_rate,
        itc_eligible=itc_eligible,
        gst_amount=gst_amount if gst_amount is not None else round(amount * gst_rate / (100 + gst_rate), 2),
        itc_amount=itc_amount,
        confidence=0.95
    )
    return txn


def test_financial_statements_module_generates_all_sections():
    txns = [
        make_transaction(500000, "credit", "ACME Corp", datetime(2026, 4, 1), "Retail & E-commerce", "business", gst_rate=18.0, itc_eligible=False),
        make_transaction(120000, "debit", "Office Supplies", datetime(2026, 4, 2), "Office Expenses", "business", gst_rate=18.0, itc_eligible=True, itc_amount=18305.08)
    ]

    statements = get_financial_statements(txns)
    assert "profit_and_loss" in statements
    assert "balance_sheet" in statements
    assert "cash_flow_statement" in statements
    assert statements["profit_and_loss"]["net_profit"] >= 0
    assert statements["balance_sheet"]["equity"]["retained_earnings"] is not None


def test_income_tax_agent_estimates_deductions_and_tax():
    txns = [
        make_transaction(300000, "credit", "Salary", datetime(2026, 4, 1), "Payroll", "personal", gst_rate=0.0, itc_eligible=False),
        make_transaction(120000, "debit", "LIC Premium", datetime(2026, 4, 10), "Insurance", "personal", gst_rate=0.0, itc_eligible=False),
        make_transaction(60000, "debit", "Health Checkup", datetime(2026, 4, 15), "Healthcare", "personal", gst_rate=0.0, itc_eligible=False)
    ]

    summary = get_income_tax_summary(txns)
    assert "taxable_income_summary" in summary
    assert summary["taxable_income_summary"]["deductions"]["80C"] >= 0
    assert summary["tax_liability"]["total_tax_liability"] >= 0


def test_reconciliation_agent_detects_duplicate_transactions():
    txns = [
        make_transaction(1200, "debit", "Cafe Coffee", datetime(2026, 4, 4), "Food & Beverage", "personal"),
        make_transaction(1200, "debit", "Cafe Coffee", datetime(2026, 4, 4), "Food & Beverage", "personal"),
        make_transaction(2000, "credit", "Freelance Payment", datetime(2026, 4, 5), "Retail & E-commerce", "business")
    ]

    report = get_reconciliation_report(txns)
    assert report["issues"]["summary"]["duplicate_count"] == 1
    assert report["calculated_closing_balance"] == 2000 - 2400


def test_audit_agent_flags_gst_mismatch_and_low_confidence():
    txn = make_transaction(10000, "debit", "Vendor Ltd", datetime(2026, 4, 8), "Office Expenses", "business", gst_rate=18.0, itc_eligible=True, gst_amount=100.0, itc_amount=100.0)
    txn.confidence = 0.35
    report = get_audit_report([txn])
    assert report["summary"]["gst_issues_count"] >= 1
    assert report["summary"]["suspicious_transactions_count"] >= 1
