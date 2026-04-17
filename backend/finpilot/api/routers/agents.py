"""
Agents Router – Exposes modular intelligence endpoints and the master Orchestrator.
"""

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from finpilot.api.deps import fetch_user_transactions

# Agent core logic imports
from finpilot.agents.expense_agent import get_expense_summary
from finpilot.agents.profit_agent import get_profit_summary
from finpilot.agents.gst_agent import analyze_itc_opportunities
from finpilot.agents.tax_savings_agent import get_tax_insights
from finpilot.agents.bookkeeping_agent import get_bookkeeping_summary
from finpilot.agents.reconciliation_agent import get_reconciliation_report
from finpilot.agents.orchestrator_agent import execute_goal

router = APIRouter(tags=["Agents"])

class OrchestratorPayload(BaseModel):
    message: str  # Natural language query, e.g., "What were my total expenses last month?"

@router.post("/orchestrate/{user_id}")
def orchestrate_route(user_id: str, payload: OrchestratorPayload):
    """
    Master entry point for intelligent conversational orchestration.
    Maintains graph-based memory per thread (user_id).
    """
    return execute_goal(user_id, payload.message)


@router.get("/insights/{user_id}")
def insights_route(user_id: str):
    """High-level financial insights targeted at a dashboard."""
    txns = fetch_user_transactions(user_id)
    profit_data  = get_profit_summary(txns)
    expense_data = get_expense_summary(txns)
    tax_data     = get_tax_insights(txns)

    return {
        "user_id": user_id,
        "financial_overview": {
            "period": "Last 30 days",
            "net_profit": profit_data["overall"]["net_profit"],
            "total_revenue": profit_data["overall"]["total_revenue"],
            "total_expenses": profit_data["overall"]["total_expenses"],
            "profit_margin_percent": profit_data["overall"]["profit_margin_percent"],
            "transactions_processed": profit_data["overall"]["transaction_count"],
        },
        "top_expense_categories": {
            cat: data["total_expenses"]
            for cat, data in sorted(
                expense_data.get("by_category", {}).items(),
                key=lambda x: x[1]["total_spent"],
                reverse=True
            )[:5]
        },
        "tax_opportunities": {
            "potential_monthly_savings": tax_data["summary"]["potential_savings_per_month"],
            "quick_wins": tax_data["quick_wins"],
            "total_action_items": tax_data["summary"]["total_action_items"],
        },
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/expenses/{user_id}")
def expenses_route(user_id: str):
    txns = fetch_user_transactions(user_id)
    return get_expense_summary(txns)


@router.get("/profit/{user_id}")
def profit_route(user_id: str):
    txns = fetch_user_transactions(user_id)
    return get_profit_summary(txns)


@router.get("/tax-savings/{user_id}")
def tax_savings_route(user_id: str):
    txns = fetch_user_transactions(user_id)
    insights = get_tax_insights(txns)
    return {
        "user_id": user_id,
        "tax_insights": insights,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/bookkeeping/{user_id}")
def bookkeeping_route(user_id: str):
    txns = fetch_user_transactions(user_id)
    summary = get_bookkeeping_summary(txns)
    return {
        "user_id": user_id,
        "bookkeeping_summary": summary,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/reconciliation/{user_id}")
def reconciliation_route(user_id: str):
    txns = fetch_user_transactions(user_id)
    report = get_reconciliation_report(txns)
    return {
        "user_id": user_id,
        "reconciliation_report": report,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/gst/{user_id}")
def gst_route(user_id: str):
    txns = fetch_user_transactions(user_id)
    return analyze_itc_opportunities(txns)


@router.get("/actions/{user_id}")
def actions_route(user_id: str):
    """
    Actionable dashboard cards mapped from various diagnostic evaluations.
    """
    txns = fetch_user_transactions(user_id)
    actions = []

    expenses = get_expense_summary(txns)
    profits  = get_profit_summary(txns)
    itc_ops  = analyze_itc_opportunities(txns)

    # 1. Red Cards
    for anomaly in expenses.get("anomalies", []):
        amt = anomaly.get("transaction", {}).get("amount", None)
        actions.append({
            "priority": "red",
            "title": "Unusual Spending Outlier Detected",
            "message": anomaly.get("anomaly_reason", "High mathematical variance explicitly defined bounds."),
            "amount": amt,
        })

    net_profit = profits.get("overall", {}).get("net_profit", 0.0)
    if net_profit < 0:
        actions.append({
            "priority": "red",
            "title": "Deficit Bounds Alert",
            "message": "You're operating at a loss this period. Review your top expense categories to cut costs.",
            "amount": abs(net_profit),
        })

    # 2. Amber Cards
    missed_itc = itc_ops.get("missed_itc_count", 0)
    if missed_itc > 0:
        actions.append({
            "priority": "amber",
            "title": "Missed Input Tax Credit Diagnostics",
            "message": f"You have {missed_itc} transactions we couldn't classify confidently. Review them to unlock potential ITC claims.",
            "amount": None,
        })

    low_conf_count = sum(1 for t in txns if t.confidence <= 0.4)
    if low_conf_count > 0:
        actions.append({
            "priority": "amber",
            "title": "Review Classification Thresholds natively",
            "message": f"AI couldn't classify {low_conf_count} transactions with high confidence. Review and tag them manually.",
            "amount": None,
        })

    # 3. Green Cards
    claimable_itc = itc_ops.get("total_itc_claimable", 0.0)
    if claimable_itc > 0:
        actions.append({
            "priority": "green",
            "title": "Input Tax Credit Available",
            "message": f"You can claim ₹{claimable_itc:,.2f} in GST credits. File your ITC claims to improve cashflow.",
            "amount": claimable_itc,
        })

    if net_profit > 0:
        actions.append({
            "priority": "green",
            "title": "Business is Profitable",
            "message": f"You made ₹{net_profit:,.2f} this period after expenses and GST recovery. Keep it up.",
            "amount": net_profit,
        })

    return {"actions": actions, "user_id": user_id}
