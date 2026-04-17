"""
Expense Agent

Aggregates categorized expenses and detects spending anomalies using
standard deviation analysis across category + party groupings.
"""

import statistics
from finpilot.models.transaction import Transaction


def categorize_expenses(transactions: list[Transaction]) -> dict:
    """Group and aggregate all debit transactions by GST category."""
    by_category: dict = {}
    total_business = 0.0
    total_personal = 0.0
    count = 0

    for txn in transactions:
        if txn.type != "debit":
            continue

        category = txn.category or "Uncategorized"
        nature   = txn.business_nature or "business"

        if category not in by_category:
            by_category[category] = {
                "total_spent": 0.0,
                "transaction_count": 0,
                "average_transaction": 0.0,
                "nature": nature,
                "transactions": [],
            }

        by_category[category]["total_spent"]        += txn.amount
        by_category[category]["transaction_count"]  += 1
        by_category[category]["transactions"].append(txn.to_dict())

        if nature == "personal":
            total_personal += txn.amount
        else:
            total_business += txn.amount
        count += 1

    top_category = None
    max_spent    = -1.0

    for cat, data in by_category.items():
        if data["transaction_count"] > 0:
            data["average_transaction"] = round(data["total_spent"] / data["transaction_count"], 2)
        data["total_spent"] = round(data["total_spent"], 2)
        if data["total_spent"] > max_spent:
            max_spent    = data["total_spent"]
            top_category = cat

    return {
        "by_category":             by_category,
        "total_business_expenses": round(total_business, 2),
        "total_personal_expenses": round(total_personal, 2),
        "total_expenses":          round(total_business + total_personal, 2),
        "top_category":            top_category,
        "transaction_count":       count,
    }


def detect_anomalies(transactions: list[Transaction]) -> list[dict]:
    """
    Flag transactions that deviate more than 2 standard deviations
    above the median for their category + party group.
    Requires at least 3 samples per group for statistical validity.
    """
    by_group: dict[str, list[Transaction]] = {}

    for txn in transactions:
        if txn.type != "debit":
            continue
        key = f"{txn.category or 'Uncategorized'}|{(txn.party or '').lower()}"
        by_group.setdefault(key, []).append(txn)

    anomalies: list[dict] = []

    for group_key, txns in by_group.items():
        if len(txns) < 3:
            continue
        amounts = [t.amount for t in txns]
        median  = statistics.median(amounts)
        std_dev = statistics.stdev(amounts)
        if std_dev == 0:
            continue
        threshold = median + (2 * std_dev)
        cat = group_key.split("|")[0]
        for txn in txns:
            if txn.amount > threshold:
                multiplier = round(txn.amount / median, 1)
                anomalies.append({
                    "transaction":   txn.to_dict(),
                    "category":      cat,
                    "median_amount": round(median, 2),
                    "std_dev":       round(std_dev, 2),
                    "anomaly_reason": (
                        f"{txn.party} payment of ₹{txn.amount:,.2f} is unusually high — "
                        f"{multiplier}x above your typical ₹{median:,.2f}."
                    ),
                })

    return anomalies


def get_expense_summary(transactions: list[Transaction]) -> dict:
    """Unified expense summary combining categorization and anomaly detection."""
    categorized = categorize_expenses(transactions)
    anomalies   = detect_anomalies(transactions)
    top_cat     = categorized.get("top_category")

    insight = "No valid expense data recorded or parsed this period."
    if top_cat:
        top_spent = categorized["by_category"][top_cat]["total_spent"]
        top_count = categorized["by_category"][top_cat]["transaction_count"]
        insight = (
            f"Your highest spend this period is {top_cat} at "
            f"₹{top_spent:,.2f} across {top_count} transactions."
        )

    return {
        "categories":    categorized["by_category"],
        "total_expenses":categorized["total_expenses"],
        "top_category":  top_cat,
        "anomalies":     anomalies,
        "anomaly_count": len(anomalies),
        "insight":       insight,
    }
