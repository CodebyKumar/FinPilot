"""
Tax Savings Agent - Actionable Recommendations

Analyzes financial data and suggests:
- ITC optimization opportunities
- Expense categorization gaps
- Tax-saving strategies
- GST compliance tips
- Quarterly planning advice
"""

from pocket_cfo_parser.models.transaction import Transaction
from collections import defaultdict


def find_missed_itc_opportunities(transactions: list[Transaction]) -> list[dict]:
    """
    Identifies transactions that might be ITC-eligible but not claimed.
    """
    opportunities = []
    
    for txn in transactions:
        if txn.type == "debit" and txn.confidence <= 0.7:
            # Low confidence = might be misclassified
            itc_eligible = getattr(txn, "itc_eligible", False)
            
            if not itc_eligible:
                # Could potentially be ITC-eligible with correct classification
                opportunities.append({
                    "date": txn.date.isoformat(),
                    "party": txn.party,
                    "amount": txn.amount,
                    "current_category": txn.category,
                    "confidence": txn.confidence,
                    "recommendation": f"Review if '{txn.party}' provides ITC-eligible services. If yes, correct to proper category to claim GST recovery.",
                    "potential_recovery": round(getattr(txn, "gst_amount", (txn.amount * 0.18) / 1.18), 2)
                })
    
    return opportunities


def analyze_expense_gaps(transactions: list[Transaction]) -> list[dict]:
    """
    Identifies expense categories that could save taxes if optimized.
    """
    recommendations = []
    
    expense_by_category = defaultdict(lambda: {"amount": 0, "count": 0})
    for txn in transactions:
        if txn.type == "debit":
            cat = txn.category or "Uncategorized"
            expense_by_category[cat]["amount"] += txn.amount
            expense_by_category[cat]["count"] += 1
    
    # Analyze patterns
    
    # 1. High "Uncategorized" spending = potential tax relief missed
    uncategorized = expense_by_category.get("Uncategorized", {})
    if uncategorized.get("amount", 0) > 1000:
        recommendations.append({
            "priority": "high",
            "title": "Categorize Uncategorized Spending",
            "description": f"You have ₹{uncategorized['amount']:,.2f} in 'Uncategorized' expenses ({uncategorized['count']} txns). Proper categorization could unlock GST credit claims.",
            "potential_savings": round(uncategorized["amount"] * 0.10, 2),  # Rough estimate
            "action": "Review each transaction and tag with correct category (Travel, Office, etc.)"
        })
    
    # 2. High food/beverage spending (not ITC eligible)
    food_txns = sum(v["amount"] for k, v in expense_by_category.items() if "food" in k.lower())
    if food_txns > 500:
        recommendations.append({
            "priority": "medium",
            "title": "Meal Expenses - Personal vs. Business",
            "description": f"You're spending ₹{food_txns:,.2f} on food/beverage (no GST benefit). Ensure only business meals are recorded.",
            "potential_savings": 0,  # Food/beverage is 5% GST, minimal recovery
            "action": "Remove purely personal meals; keep only client entertainment and business meetings."
        })
    
    # 3. Fuel spending (GST exempt)
    fuel_txns = sum(v["amount"] for k, v in expense_by_category.items() if "fuel" in k.lower())
    if fuel_txns > 100:
        recommendations.append({
            "priority": "low",
            "title": "Fuel Expenses (No GST Recovery)",
            "description": f"Fuel is GST-exempt (no ITC benefit). ₹{fuel_txns:,.2f} spent with no tax deduction possible.",
            "potential_savings": 0,
            "action": "Track these for income tax deduction under transportation costs instead."
        })
    
    return recommendations


def suggest_expense_optimization(transactions: list[Transaction]) -> list[dict]:
    """
    Suggests ways to optimize expenses and reduce tax burden.
    """
    suggestions = []
    
    transactions_by_party = defaultdict(list)
    for txn in transactions:
        if txn.type == "debit":
            transactions_by_party[txn.party].append(txn)
    
    # 1. Repeated small expenses
    for party, txns in transactions_by_party.items():
        if len(txns) > 5:
            total = sum(t.amount for t in txns)
            avg = total / len(txns)
            
            if avg < 500:
                suggestions.append({
                    "priority": "medium",
                    "title": f"Consolidate {party} Purchases",
                    "description": f"{len(txns)} transactions to {party} (avg ₹{avg:.0f} each, total ₹{total:,.2f}). Consider bulk buying or contract rates.",
                    "potential_savings": round(total * 0.05, 2),  # Rough 5% savings estimate
                    "action": f"Negotiate bulk discounts or monthly contracts with {party} for 5-15% rate reduction"
                })
    
    return suggestions


def generate_tax_saving_plan(transactions: list[Transaction]) -> dict:
    """
    Comprehensive tax-saving strategy for the business.
    """
    missed_itc = find_missed_itc_opportunities(transactions)
    gaps = analyze_expense_gaps(transactions)
    optimizations = suggest_expense_optimization(transactions)
    
    # Calculate potential total savings
    potential_savings = 0.0
    for rec in gaps + optimizations:
        potential_savings += rec.get("potential_savings", 0)
    
    for opp in missed_itc:
        potential_savings += opp.get("potential_recovery", 0)
    
    return {
        "potential_annual_savings": round(potential_savings * 12, 2),  # Annualize
        "potential_monthly_savings": round(potential_savings, 2),
        "missed_itc_opportunities": missed_itc,
        "expense_gaps": gaps,
        "optimization_tips": optimizations,
        "total_recommendations": len(missed_itc) + len(gaps) + len(optimizations),
        "generated_at": __import__('datetime').datetime.now().isoformat()
    }


def get_tax_insights(transactions: list[Transaction]) -> dict:
    """
    Quick tax insights for the user dashboard.
    """
    plan = generate_tax_saving_plan(transactions)
    
    # Extract key metrics
    high_priority = [r for r in plan["expense_gaps"] if r.get("priority") == "high"]
    
    return {
        "summary": {
            "potential_savings_per_month": plan["potential_monthly_savings"],
            "potential_savings_per_year": plan["potential_annual_savings"],
            "total_action_items": plan["total_recommendations"],
            "high_priority_items": len(high_priority)
        },
        "quick_wins": [r["title"] for r in high_priority[:3]],
        "full_plan": plan
    }
