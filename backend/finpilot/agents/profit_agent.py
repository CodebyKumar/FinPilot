"""
Profit Agent v2 – Comprehensive Financial Analytics

Calculates business profit with:
- Business vs personal revenue/expense separation
- GST impact analysis
- ITC recovery impact
- Category-level profit breakdown
- Cash flow trend analysis
"""

from collections import defaultdict
from datetime import datetime, timedelta

from finpilot.models.transaction import Transaction


def calculate_comprehensive_profit(transactions: list[Transaction]) -> dict:
    """Core profit calculation: Revenue - Expenses - GST Paid + ITC Claimable."""
    empty = {
        "total_revenue": 0.0, "total_expenses": 0.0, "total_gst_paid": 0.0,
        "total_itc_claimable": 0.0, "gross_profit": 0.0, "net_profit": 0.0,
        "profit_margin_percent": 0.0, "transaction_count": 0,
    }
    if not transactions:
        return empty

    total_revenue = total_personal_revenue = 0.0
    total_business = total_personal = 0.0
    total_gst = total_itc = 0.0
    revenue_txns = expense_txns = 0

    for txn in transactions:
        if txn.type == "credit":
            if getattr(txn, "business_nature", "business") == "personal":
                total_personal_revenue += txn.amount
            else:
                total_revenue += txn.amount
            revenue_txns += 1
        elif txn.type == "debit":
            expense_txns += 1
            if getattr(txn, "business_nature", "business") == "personal":
                total_personal += txn.amount
            else:
                total_business += txn.amount
            gst_rate   = getattr(txn, "gst_rate", 0.0)
            gst_amount = getattr(txn, "gst_amount", None)
            if gst_amount is None:
                gst_amount = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0
            total_gst += gst_amount
            if getattr(txn, "itc_eligible", False):
                total_itc += getattr(txn, "itc_amount", gst_amount)

    gross_profit = total_revenue - total_business
    net_profit   = gross_profit + total_itc
    margin       = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    return {
        "total_revenue":           round(total_revenue, 2),
        "total_personal_revenue":  round(total_personal_revenue, 2),
        "total_business_expenses": round(total_business, 2),
        "total_personal_expenses": round(total_personal, 2),
        "total_expenses":          round(total_business + total_personal, 2),
        "total_gst_paid":          round(total_gst, 2),
        "total_itc_claimable":     round(total_itc, 2),
        "gross_profit":            round(gross_profit, 2),
        "net_profit":              round(net_profit, 2),
        "profit_margin_percent":   round(margin, 2),
        "revenue_transactions":    revenue_txns,
        "expense_transactions":    expense_txns,
        "transaction_count":       len(transactions),
    }


def calculate_category_profits(transactions: list[Transaction]) -> dict:
    """Profit breakdown by expense category."""
    category_data: dict = defaultdict(lambda: {
        "expenses": 0.0, "count": 0, "gst_paid": 0.0,
        "itc_claimable": 0.0, "transactions": [],
    })

    for txn in transactions:
        if txn.type != "debit":
            continue
        cat = txn.category or "Uncategorized"
        category_data[cat]["expenses"] += txn.amount
        category_data[cat]["count"]    += 1
        category_data[cat]["transactions"].append({
            "date": txn.date.isoformat(), "party": txn.party, "amount": txn.amount,
        })
        gst_rate   = getattr(txn, "gst_rate", 0.0)
        gst_amount = getattr(txn, "gst_amount", None)
        if gst_amount is None:
            gst_amount = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0
        category_data[cat]["gst_paid"] += gst_amount
        if getattr(txn, "itc_eligible", False):
            category_data[cat]["itc_claimable"] += getattr(txn, "itc_amount", gst_amount)

    result = {}
    for cat, data in category_data.items():
        cnt = data["count"]
        result[cat] = {
            "total_expenses":    round(data["expenses"], 2),
            "transaction_count": cnt,
            "average_expense":   round(data["expenses"] / cnt, 2) if cnt else 0.0,
            "gst_paid":          round(data["gst_paid"], 2),
            "itc_claimable":     round(data["itc_claimable"], 2),
            "sample_transactions": data["transactions"][:5],
        }
    return result


def analyze_spending_trends(transactions: list[Transaction], days: int = 30) -> dict:
    """Analyse daily spending patterns over a given period."""
    cutoff      = datetime.now() - timedelta(days=days)
    recent      = [t for t in transactions if t.date >= cutoff]
    daily_spend: dict[str, float] = defaultdict(float)

    for txn in recent:
        if txn.type == "debit":
            daily_spend[txn.date.strftime("%Y-%m-%d")] += txn.amount

    if not daily_spend:
        return {
            "period_days": days, "total_spending": 0.0, "average_daily": 0.0,
            "max_spend_day": None, "min_spend_day": None, "trend": "Insufficient data",
        }

    total   = sum(daily_spend.values())
    max_day = max(daily_spend, key=daily_spend.__getitem__)
    min_day = min(daily_spend, key=daily_spend.__getitem__)

    return {
        "period_days":        days,
        "total_spending":     round(total, 2),
        "average_daily":      round(total / len(daily_spend), 2),
        "max_spend_day":      max_day,
        "max_spend_amount":   round(daily_spend[max_day], 2),
        "min_spend_day":      min_day,
        "min_spend_amount":   round(daily_spend[min_day], 2),
        "transaction_count":  len(recent),
    }


def get_profit_summary(transactions: list[Transaction]) -> dict:
    """Complete profit summary combining all sub-analyses."""
    overall  = calculate_comprehensive_profit(transactions)
    by_cat   = calculate_category_profits(transactions)
    trends   = analyze_spending_trends(transactions, days=30)

    net = overall["net_profit"]
    overall["verdict"] = (
        f"Profitable — you made ₹{net:,.2f} after business expenses and GST recovery"
        if net > 0 else (
            "Break even — revenue exactly covers business expenses"
            if net == 0 else
            f"Loss — you are ₹{abs(net):,.2f} short after business expense and GST impact"
        )
    )
    overall["note"] = (
        f"Business expenses are ₹{overall['total_business_expenses']:,.2f} and "
        f"personal expenses are ₹{overall['total_personal_expenses']:,.2f}."
    )

    return {
        "overall":          overall,
        "by_category":      by_cat,
        "spending_trends":  trends,
        "generated_at":     datetime.now().isoformat(),
    }
