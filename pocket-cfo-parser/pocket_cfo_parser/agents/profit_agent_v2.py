"""
Profit Agent v2 - Real Financial Analytics

Calculates actual business profit with:
- Revenue vs Expenses breakdown
- GST impact analysis
- ITC recovery impact
- Profit margins per category
- Cashflow analysis
"""

from collections import defaultdict
from datetime import datetime, timedelta
from pocket_cfo_parser.models.transaction import Transaction


def categorize_transactions(transactions: list[Transaction]) -> dict:
    """
    Organizes transactions by category and type.
    """
    by_category = defaultdict(lambda: {"credit": [], "debit": []})
    
    for txn in transactions:
        if txn.type == "credit":
            by_category[txn.category]["credit"].append(txn)
        else:
            by_category[txn.category]["debit"].append(txn)
    
    return dict(by_category)


def calculate_comprehensive_profit(transactions: list[Transaction]) -> dict:
    """
    Core profit calculation:
    Revenue - Expenses - GST Paid + ITC Claimable = Net Profit
    """
    if not transactions:
        return {
            "total_revenue": 0.0,
            "total_expenses": 0.0,
            "total_gst_paid": 0.0,
            "total_itc_claimable": 0.0,
            "gross_profit": 0.0,
            "net_profit": 0.0,
            "profit_margin_percent": 0.0,
            "transaction_count": 0
        }
    
    total_revenue = 0.0
    total_personal_revenue = 0.0
    total_business_expenses = 0.0
    total_personal_expenses = 0.0
    total_gst_paid = 0.0
    total_itc_claimable = 0.0
    
    revenue_txns = 0
    expense_txns = 0
    
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
                total_personal_expenses += txn.amount
            else:
                total_business_expenses += txn.amount
            
            gst_amount = getattr(txn, "gst_amount", None)
            if gst_amount is None:
                gst_rate = getattr(txn, "gst_rate", 0.0)
                gst_amount = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0
            total_gst_paid += gst_amount
            
            if getattr(txn, "itc_eligible", False):
                total_itc_claimable += getattr(txn, "itc_amount", gst_amount)
    
    gross_profit = total_revenue - total_business_expenses
    net_profit = gross_profit + total_itc_claimable  # ITC improves profit
    
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_personal_revenue": round(total_personal_revenue, 2),
        "total_business_expenses": round(total_business_expenses, 2),
        "total_personal_expenses": round(total_personal_expenses, 2),
        "total_expenses": round(total_business_expenses + total_personal_expenses, 2),
        "total_gst_paid": round(total_gst_paid, 2),
        "total_itc_claimable": round(total_itc_claimable, 2),
        "gross_profit": round(gross_profit, 2),
        "net_profit": round(net_profit, 2),
        "profit_margin_percent": round(profit_margin, 2),
        "revenue_transactions": revenue_txns,
        "expense_transactions": expense_txns,
        "transaction_count": len(transactions)
    }


def calculate_category_profits(transactions: list[Transaction]) -> dict:
    """
    Profit breakdown by expense category.
    """
    category_data = defaultdict(lambda: {
        "expenses": 0.0,
        "count": 0,
        "gst_paid": 0.0,
        "itc_claimable": 0.0,
        "transactions": []
    })
    
    for txn in transactions:
        if txn.type == "debit":
            category = txn.category or "Uncategorized"
            category_data[category]["expenses"] += txn.amount
            category_data[category]["count"] += 1
            category_data[category]["transactions"].append({
                "date": txn.date.isoformat(),
                "party": txn.party,
                "amount": txn.amount
            })
            
            gst_on_txn = getattr(txn, "gst_amount", None)
            if gst_on_txn is None:
                gst_rate = getattr(txn, "gst_rate", 0.0)
                gst_on_txn = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0
            category_data[category]["gst_paid"] += gst_on_txn
            if getattr(txn, "itc_eligible", False):
                category_data[category]["itc_claimable"] += getattr(txn, "itc_amount", gst_on_txn)
    
    # Format response
    result = {}
    for cat, data in category_data.items():
        result[cat] = {
            "total_expenses": round(data["expenses"], 2),
            "transaction_count": data["count"],
            "average_expense": round(data["expenses"] / data["count"], 2) if data["count"] > 0 else 0.0,
            "gst_paid": round(data["gst_paid"], 2),
            "itc_claimable": round(data["itc_claimable"], 2),
            "sample_transactions": data["transactions"][:5]
        }
    
    return result


def analyze_spending_trends(transactions: list[Transaction], days: int = 30) -> dict:
    """
    Analyzes spending patterns over a period.
    """
    now = datetime.now()
    cutoff_date = now - timedelta(days=days)
    
    recent_txns = [t for t in transactions if t.date >= cutoff_date]
    
    daily_spend = defaultdict(float)
    for txn in recent_txns:
        if txn.type == "debit":
            date_key = txn.date.strftime("%Y-%m-%d")
            daily_spend[date_key] += txn.amount
    
    if not daily_spend:
        return {
            "period_days": days,
            "total_spending": 0.0,
            "average_daily": 0.0,
            "max_spend_day": None,
            "min_spend_day": None,
            "trend": "Insufficient data"
        }
    
    total = sum(daily_spend.values())
    max_day = max(daily_spend, key=daily_spend.get)
    min_day = min(daily_spend, key=daily_spend.get)
    
    return {
        "period_days": days,
        "total_spending": round(total, 2),
        "average_daily": round(total / len(daily_spend), 2),
        "max_spend_day": max_day,
        "max_spend_amount": round(daily_spend[max_day], 2),
        "min_spend_day": min_day,
        "min_spend_amount": round(daily_spend[min_day], 2),
        "transaction_count": len(recent_txns)
    }


def get_profit_summary(transactions: list[Transaction]) -> dict:
    """
    Complete profit summary for CA report.
    """
    overall_profit = calculate_comprehensive_profit(transactions)
    category_profits = calculate_category_profits(transactions)
    spending_trends = analyze_spending_trends(transactions, days=30)
    
    overall_profit["verdict"] = (
        f"Profitable — you made ₹{overall_profit['net_profit']:,.2f} after business expenses and GST recovery"
        if overall_profit["net_profit"] > 0 else (
            "Break even — revenue exactly covers business expenses" if overall_profit["net_profit"] == 0 else
            f"Loss — you are ₹{abs(overall_profit['net_profit']):,.2f} short after business expense and GST impact"
        )
    )
    overall_profit["note"] = (
        f"Business expenses are ₹{overall_profit['total_business_expenses']:,.2f} and personal expenses are ₹{overall_profit['total_personal_expenses']:,.2f}."
    )

    return {
        "overall": overall_profit,
        "by_category": category_profits,
        "spending_trends": spending_trends,
        "generated_at": datetime.now().isoformat()
    }
