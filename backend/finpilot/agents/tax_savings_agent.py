"""
Tax Savings Agent – Actionable Tax Optimization Recommendations

Analyses financial data and suggests:
- Missed ITC opportunities
- Expense categorization gaps
- Tax-saving strategies
- GST compliance tips
"""

from collections import defaultdict
from datetime import datetime

from finpilot.models.transaction import Transaction


def find_missed_itc_opportunities(transactions: list[Transaction]) -> list[dict]:
    """Identify debit transactions that could be ITC-eligible but currently aren't classified as such."""
    opportunities = []
    for txn in transactions:
        if txn.type == "debit" and txn.confidence <= 0.7:
            if not getattr(txn, "itc_eligible", False):
                opportunities.append({
                    "date":             txn.date.isoformat(),
                    "party":            txn.party,
                    "amount":           txn.amount,
                    "current_category": txn.category,
                    "confidence":       txn.confidence,
                    "recommendation": (
                        f"Review if '{txn.party}' provides ITC-eligible services. "
                        "If yes, correct to proper category to claim GST recovery."
                    ),
                    "potential_recovery": round(
                        getattr(txn, "gst_amount", (txn.amount * 0.18) / 1.18), 2
                    ),
                })
    return opportunities


def analyze_expense_gaps(transactions: list[Transaction]) -> list[dict]:
    """Identify expense categories where tax optimisation could be applied."""
    recommendations = []
    expense_by_category: dict = defaultdict(lambda: {"amount": 0.0, "count": 0})

    for txn in transactions:
        if txn.type == "debit":
            cat = txn.category or "Uncategorized"
            expense_by_category[cat]["amount"] += txn.amount
            expense_by_category[cat]["count"]  += 1

    uncategorized = expense_by_category.get("Uncategorized", {})
    if uncategorized.get("amount", 0) > 1000:
        recommendations.append({
            "priority": "high",
            "title":    "Categorize Uncategorized Spending",
            "description": (
                f"You have ₹{uncategorized['amount']:,.2f} in 'Uncategorized' expenses "
                f"({uncategorized['count']} txns). Proper categorization could unlock GST credit claims."
            ),
            "potential_savings": round(uncategorized["amount"] * 0.10, 2),
            "action": "Review each transaction and tag with correct category (Travel, Office, etc.)",
        })

    food_total = sum(v["amount"] for k, v in expense_by_category.items() if "food" in k.lower())
    if food_total > 500:
        recommendations.append({
            "priority": "medium",
            "title":    "Meal Expenses – Personal vs. Business",
            "description": (
                f"You're spending ₹{food_total:,.2f} on food/beverage (no GST benefit). "
                "Ensure only business meals are recorded."
            ),
            "potential_savings": 0,
            "action": "Remove purely personal meals; keep only client entertainment and business meetings.",
        })

    fuel_total = sum(v["amount"] for k, v in expense_by_category.items() if "fuel" in k.lower())
    if fuel_total > 100:
        recommendations.append({
            "priority": "low",
            "title":    "Fuel Expenses (No GST Recovery)",
            "description": (
                f"Fuel is GST-exempt (no ITC benefit). ₹{fuel_total:,.2f} spent with no tax deduction possible."
            ),
            "potential_savings": 0,
            "action": "Track these for income tax deduction under transportation costs instead.",
        })

    return recommendations


def suggest_expense_optimization(transactions: list[Transaction]) -> list[dict]:
    """Suggest ways to optimize recurring expenses."""
    suggestions = []
    by_party: dict = defaultdict(list)

    for txn in transactions:
        if txn.type == "debit":
            by_party[txn.party].append(txn)

    for party, txns in by_party.items():
        if len(txns) > 5:
            total = sum(t.amount for t in txns)
            avg   = total / len(txns)
            if avg < 500:
                suggestions.append({
                    "priority": "medium",
                    "title":    f"Consolidate {party} Purchases",
                    "description": (
                        f"{len(txns)} transactions to {party} (avg ₹{avg:.0f} each, total ₹{total:,.2f}). "
                        "Consider bulk buying or contract rates."
                    ),
                    "potential_savings": round(total * 0.05, 2),
                    "action": (
                        f"Negotiate bulk discounts or monthly contracts with {party} for 5–15% rate reduction."
                    ),
                })
    return suggestions


def generate_tax_saving_plan(transactions: list[Transaction]) -> dict:
    """Build a comprehensive tax-saving strategy."""
    missed_itc    = find_missed_itc_opportunities(transactions)
    gaps          = analyze_expense_gaps(transactions)
    optimizations = suggest_expense_optimization(transactions)

    potential = sum(r.get("potential_savings", 0) for r in gaps + optimizations)
    potential += sum(o.get("potential_recovery", 0) for o in missed_itc)

    return {
        "potential_annual_savings":  round(potential * 12, 2),
        "potential_monthly_savings": round(potential, 2),
        "missed_itc_opportunities":  missed_itc,
        "expense_gaps":              gaps,
        "optimization_tips":         optimizations,
        "total_recommendations":     len(missed_itc) + len(gaps) + len(optimizations),
        "generated_at":              datetime.now().isoformat(),
    }


def get_tax_insights(transactions: list[Transaction]) -> dict:
    """Quick tax insights for the dashboard."""
    plan         = generate_tax_saving_plan(transactions)
    high_priority = [r for r in plan["expense_gaps"] if r.get("priority") == "high"]

    return {
        "summary": {
            "potential_savings_per_month": plan["potential_monthly_savings"],
            "potential_savings_per_year":  plan["potential_annual_savings"],
            "total_action_items":          plan["total_recommendations"],
            "high_priority_items":         len(high_priority),
        },
        "quick_wins": [r["title"] for r in high_priority[:3]],
        "full_plan":  plan,
    }
