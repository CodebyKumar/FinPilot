import logging
from langchain_core.tools import tool
from datetime import datetime
from typing import Any, Dict, Literal

from finpilot.api.deps import fetch_user_transactions
from finpilot.agents.bookkeeping_agent import build_bookkeeping_entries, get_bookkeeping_summary
from finpilot.agents.expense_agent import detect_anomalies, get_expense_summary
from finpilot.agents.gst_agent import analyze_itc_opportunities
from finpilot.agents.profit_agent import get_profit_summary
from finpilot.agents.reconciliation_agent import get_reconciliation_report
from finpilot.models.transaction import Transaction

logger = logging.getLogger(__name__)


def _parse_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _apply_transaction_filters(transactions: list[Transaction], filters: dict[str, Any]) -> list[Transaction]:
    if not filters:
        return transactions

    date_from = _parse_date(filters.get("date_from"))
    date_to = _parse_date(filters.get("date_to"))
    category = str(filters.get("category", "")).strip().lower()
    business_nature = str(filters.get("business_nature", "")).strip().lower()
    txn_type = str(filters.get("type", "")).strip().lower()

    min_amount = filters.get("min_amount")
    max_amount = filters.get("max_amount")
    try:
        min_amount = float(min_amount) if min_amount not in (None, "") else None
    except Exception:
        min_amount = None
    try:
        max_amount = float(max_amount) if max_amount not in (None, "") else None
    except Exception:
        max_amount = None

    filtered: list[Transaction] = []
    for txn in transactions:
        if date_from and txn.date < date_from:
            continue
        if date_to and txn.date > date_to:
            continue
        if category and (txn.category or "").strip().lower() != category:
            continue
        if business_nature and (txn.business_nature or "").strip().lower() != business_nature:
            continue
        if txn_type and (txn.type or "").strip().lower() != txn_type:
            continue
        if min_amount is not None and float(txn.amount) < min_amount:
            continue
        if max_amount is not None and float(txn.amount) > max_amount:
            continue
        filtered.append(txn)

    return filtered


def query_bookkeeping_data(
    user_id: str,
    query_type: Literal[
        "full_ledger",
        "by_category",
        "by_date_range",
        "summary_metrics",
        "anomalies",
        "gst_analysis",
    ] = "summary_metrics",
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    transactions: list[Transaction] | None = None,
) -> Dict[str, Any]:
    txns = transactions if transactions is not None else fetch_user_transactions(user_id)
    normalized_filters = filters if isinstance(filters, dict) else {}
    filtered = _apply_transaction_filters(txns, normalized_filters)
    trimmed = filtered[: max(1, min(int(limit), 1000))]

    if query_type == "full_ledger":
        return {
            "query_type": query_type,
            "count": len(trimmed),
            "total_after_filter": len(filtered),
            "filters": normalized_filters,
            "entries": build_bookkeeping_entries(trimmed),
        }

    if query_type == "by_category":
        expense_summary = get_expense_summary(trimmed)
        return {
            "query_type": query_type,
            "count": len(trimmed),
            "filters": normalized_filters,
            "categories": expense_summary.get("categories", {}),
            "total_expenses": expense_summary.get("total_expenses", 0.0),
            "top_category": expense_summary.get("top_category"),
        }

    if query_type == "by_date_range":
        ledger = build_bookkeeping_entries(trimmed)
        return {
            "query_type": query_type,
            "count": len(trimmed),
            "filters": normalized_filters,
            "entries": ledger,
            "summary": get_bookkeeping_summary(trimmed).get("balance_summary", {}),
        }

    if query_type == "anomalies":
        anomalies = detect_anomalies(trimmed)
        return {
            "query_type": query_type,
            "count": len(trimmed),
            "filters": normalized_filters,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
        }

    if query_type == "gst_analysis":
        gst = analyze_itc_opportunities(trimmed)
        return {
            "query_type": query_type,
            "count": len(trimmed),
            "filters": normalized_filters,
            "gst_analysis": gst,
        }

    bookkeeping = get_bookkeeping_summary(trimmed)
    return {
        "query_type": "summary_metrics",
        "count": len(trimmed),
        "filters": normalized_filters,
        "summary": bookkeeping.get("balance_summary", {}),
        "insights": bookkeeping.get("balance_summary", {}).get("insights", []),
    }


@tool
def query_bookkeeping(
    user_id: str,
    query_type: Literal[
        "full_ledger",
        "by_category",
        "by_date_range",
        "summary_metrics",
        "anomalies",
        "gst_analysis",
    ] = "summary_metrics",
    filters: dict[str, Any] | None = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Query bookkeeping records with filters for ledger, category, anomaly, GST, and summary views."""
    return query_bookkeeping_data(
        user_id=user_id,
        query_type=query_type,
        filters=filters,
        limit=limit,
        transactions=None,
    )

@tool
def analyze_expenses(user_id: str) -> Dict[str, Any]:
    """Use this tool to get an analysis of the user's expenses, categorizations, and identification of spending outliers."""
    txns = fetch_user_transactions(user_id)
    return get_expense_summary(txns)

@tool
def analyze_profits(user_id: str) -> Dict[str, Any]:
    """Use this tool to calculate operating net profits, revenue vs costs, and profit margins."""
    txns = fetch_user_transactions(user_id)
    return get_profit_summary(txns)

@tool
def run_reconciliation(user_id: str) -> Dict[str, Any]:
    """Use this tool to check for duplicate transactions, mismatched balances, and general ledger errors."""
    txns = fetch_user_transactions(user_id)
    return get_reconciliation_report(txns)

@tool
def get_bookkeeping_ledgers(user_id: str) -> Dict[str, Any]:
    """Use this tool to retrieve a breakdown of journal entries and general ledger structures."""
    txns = fetch_user_transactions(user_id)
    return get_bookkeeping_summary(txns)
