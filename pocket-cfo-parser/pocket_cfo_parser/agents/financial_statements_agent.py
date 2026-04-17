"""
Financial Statements Agent

Generates P&L, simplified balance sheet, and cash flow statements from transactions.
"""

from collections import defaultdict
from datetime import datetime
from pocket_cfo_parser.models.transaction import Transaction
from pocket_cfo_parser.agents.gst_agent import analyze_itc_opportunities


def _round(value: float) -> float:
    return round(value or 0.0, 2)


def generate_profit_and_loss(transactions: list[Transaction]) -> dict:
    revenue = 0.0
    other_income = 0.0
    operating_expenses = 0.0
    personal_expenses = 0.0
    expense_breakdown = defaultdict(float)

    for txn in transactions:
        if txn.type == "credit":
            if getattr(txn, "business_nature", "business") == "business":
                revenue += txn.amount
            else:
                other_income += txn.amount
        elif txn.type == "debit":
            if getattr(txn, "business_nature", "business") == "business":
                operating_expenses += txn.amount
            else:
                personal_expenses += txn.amount
            category = txn.category or "Uncategorized"
            expense_breakdown[category] += txn.amount

    itc_info = analyze_itc_opportunities(transactions)
    net_itc = itc_info.get("total_itc_claimable", 0.0)

    gross_profit = revenue - operating_expenses
    net_profit = gross_profit + net_itc
    profit_margin = (net_profit / revenue * 100) if revenue else 0.0

    return {
        "report_type": "Profit & Loss Statement",
        "generated_at": datetime.now().isoformat(),
        "total_revenue": _round(revenue),
        "other_income": _round(other_income),
        "operating_expenses": _round(operating_expenses),
        "personal_expenses": _round(personal_expenses),
        "expense_breakdown": {cat: _round(amount) for cat, amount in sorted(expense_breakdown.items(), key=lambda x: x[1], reverse=True)},
        "gross_profit": _round(gross_profit),
        "net_itc": _round(net_itc),
        "net_profit": _round(net_profit),
        "profit_margin_percent": _round(profit_margin),
        "summary": (
            f"Revenue ₹{_round(revenue):,.2f}, business expenses ₹{_round(operating_expenses):,.2f}, "
            f"ITC recovery ₹{_round(net_itc):,.2f}, net profit ₹{_round(net_profit):,.2f}."
        )
    }


def generate_balance_sheet(transactions: list[Transaction]) -> dict:
    balance = 0.0
    total_itc = 0.0
    total_output_gst = 0.0
    for txn in transactions:
        if txn.type == "credit":
            balance += txn.amount
            total_output_gst += getattr(txn, "gst_amount", txn.amount * getattr(txn, "gst_rate", 0.0) / (100 + getattr(txn, "gst_rate", 0.0)))
        else:
            balance -= txn.amount
            if getattr(txn, "itc_eligible", False):
                total_itc += getattr(txn, "itc_amount", txn.amount * getattr(txn, "gst_rate", 0.0) / (100 + getattr(txn, "gst_rate", 0.0)))

    current_assets = balance + total_itc
    current_liabilities = max(total_output_gst - total_itc, 0.0)
    equity = current_assets - current_liabilities

    return {
        "report_type": "Simplified Balance Sheet",
        "generated_at": datetime.now().isoformat(),
        "assets": {
            "cash_and_bank": _round(balance),
            "input_tax_credit_receivable": _round(total_itc),
            "total_current_assets": _round(current_assets)
        },
        "liabilities": {
            "output_gst_payable": _round(total_output_gst),
            "net_gst_liability": _round(current_liabilities),
            "total_current_liabilities": _round(current_liabilities)
        },
        "equity": {
            "retained_earnings": _round(equity),
            "total_equity_and_liabilities": _round(equity + current_liabilities)
        },
        "notes": [
            "This balance sheet is a simplified view based on transaction cash flows.",
            "GST liabilities are approximated from sales outflow and ITC claims from purchase transactions."
        ]
    }


def generate_cash_flow_statement(transactions: list[Transaction]) -> dict:
    operating_inflow = 0.0
    operating_outflow = 0.0
    investing = 0.0
    financing = 0.0
    opening_cash = 0.0
    cash_by_category = defaultdict(float)

    for txn in transactions:
        category = txn.category or "Uncategorized"
        cash_by_category[category] += txn.amount
        if txn.category and txn.category.lower() in {"investments", "financial services", "banking fees"}:
            if txn.type == "credit":
                investing += txn.amount
            else:
                investing -= txn.amount
        elif txn.category and txn.category.lower() in {"rent & real estate", "software & subscriptions", "office expenses", "utilities", "travel"}:
            if txn.type == "debit":
                operating_outflow += txn.amount
            else:
                operating_inflow += txn.amount
        else:
            if txn.type == "credit":
                operating_inflow += txn.amount
            else:
                operating_outflow += txn.amount

    net_operating = operating_inflow - operating_outflow
    net_investing = investing
    net_financing = financing
    net_change = net_operating + net_investing + net_financing
    ending_cash = opening_cash + net_change

    return {
        "report_type": "Cash Flow Statement",
        "generated_at": datetime.now().isoformat(),
        "operating_activities": {
            "cash_inflows": _round(operating_inflow),
            "cash_outflows": _round(operating_outflow),
            "net_operating_cash_flow": _round(net_operating)
        },
        "investing_activities": {
            "net_investing_cash_flow": _round(net_investing)
        },
        "financing_activities": {
            "net_financing_cash_flow": _round(net_financing)
        },
        "net_change_in_cash": _round(net_change),
        "opening_cash_balance": _round(opening_cash),
        "ending_cash_balance": _round(ending_cash),
        "category_cash_contributions": {cat: _round(amount) for cat, amount in sorted(cash_by_category.items(), key=lambda x: abs(x[1]), reverse=True)[:8]},
        "notes": [
            "This cash flow statement is based on transaction-level cash movements.",
            "Categorization to operating, investing, and financing activities is provisional and derived from expense categories."
        ]
    }


def get_financial_statements(transactions: list[Transaction]) -> dict:
    return {
        "profit_and_loss": generate_profit_and_loss(transactions),
        "balance_sheet": generate_balance_sheet(transactions),
        "cash_flow_statement": generate_cash_flow_statement(transactions)
    }
