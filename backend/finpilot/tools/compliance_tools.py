import logging
from datetime import datetime, timedelta
from langchain_core.tools import tool
from typing import Any, Dict, Literal

from finpilot.api.deps import fetch_user_transactions
from finpilot.agents.gst_agent import analyze_itc_opportunities
from finpilot.agents.tax_savings_agent import get_tax_insights
from finpilot.db.mongo import _get_db
from finpilot.services.calendar_engine import get_compliance_calendar_events

logger = logging.getLogger(__name__)


def _parse_due_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _match_deadline_type(raw_type: str, deadline_type: str) -> bool:
    expected = deadline_type.strip().lower()
    current = raw_type.strip().lower()
    if expected == "all":
        return True
    if expected == "gst":
        return "gst" in current
    if expected == "tax":
        return any(token in current for token in ("tax", "itr", "tds", "advance"))
    if expected == "audit":
        return "audit" in current
    if expected == "payment":
        return any(token in current for token in ("payment", "invoice"))
    return expected in current


def query_deadlines_data(
    user_id: str,
    filter_by: Literal["pending", "overdue", "all"] = "all",
    deadline_type: Literal["tax", "gst", "payment", "audit", "all"] = "all",
    window_days: int = 45,
    include_calendar: bool = True,
) -> dict[str, Any]:
    deadline_items = list(_get_db()["deadlines"].find({"user_id": user_id}, {"_id": 0}).sort("due_date", 1))
    today = datetime.now().date()
    window_end = today + timedelta(days=max(1, min(int(window_days), 365)))

    normalized: list[dict[str, Any]] = []
    pending = submitted = overdue = upcoming = 0

    for item in deadline_items:
        if not isinstance(item, dict):
            continue

        raw_type = str(item.get("type", "compliance")).strip()
        if not _match_deadline_type(raw_type, deadline_type):
            continue

        due_dt = _parse_due_date(item.get("due_date"))
        due_date = due_dt.date() if due_dt else None

        status = str(item.get("status", "pending")).strip().lower()
        is_submitted = bool(item.get("submitted", False))
        if is_submitted:
            status = "submitted"
        elif due_date and due_date < today:
            status = "overdue"
        elif status not in {"pending", "submitted", "overdue"}:
            status = "pending"

        if filter_by == "pending" and status != "pending":
            continue
        if filter_by == "overdue" and status != "overdue":
            continue

        if status == "pending":
            pending += 1
        elif status == "submitted":
            submitted += 1
        elif status == "overdue":
            overdue += 1

        if due_date and status == "pending" and due_date <= window_end:
            upcoming += 1

        normalized.append(
            {
                "deadline_id": item.get("deadline_id"),
                "title": item.get("title") or raw_type.title(),
                "type": raw_type,
                "due_date": due_date.isoformat() if due_date else item.get("due_date"),
                "status": status,
                "submitted": is_submitted,
                "meta": item.get("meta", {}),
            }
        )

    response: dict[str, Any] = {
        "user_id": user_id,
        "query": {
            "filter_by": filter_by,
            "deadline_type": deadline_type,
            "window_days": window_days,
        },
        "summary": {
            "total": len(normalized),
            "pending": pending,
            "submitted": submitted,
            "overdue": overdue,
            "upcoming_within_window": upcoming,
        },
        "deadlines": normalized,
    }

    if include_calendar:
        calendar = get_compliance_calendar_events(user_id)
        response["calendar_events"] = calendar.get("events", []) if isinstance(calendar, dict) else []

    return response


@tool
def query_deadlines(
    user_id: str,
    filter_by: Literal["pending", "overdue", "all"] = "all",
    deadline_type: Literal["tax", "gst", "payment", "audit", "all"] = "all",
    window_days: int = 45,
    include_calendar: bool = True,
) -> dict[str, Any]:
    """Query compliance deadlines with status and type filters, including optional calendar events."""
    return query_deadlines_data(
        user_id=user_id,
        filter_by=filter_by,
        deadline_type=deadline_type,
        window_days=window_days,
        include_calendar=include_calendar,
    )

@tool
def get_gst_itc_opportunities(user_id: str) -> Dict[str, Any]:
    """Use this tool to analyze the user's GST Input Tax Credit (ITC) opportunities, total claimable ITC, and missed ITC metrics."""
    logger.info("Executing get_gst_itc_opportunities for %s", user_id)
    txns = fetch_user_transactions(user_id)
    return analyze_itc_opportunities(txns)

@tool
def get_tax_planning_insights(user_id: str) -> Dict[str, Any]:
    """Use this tool to provide tax planning intelligence, potential tax savings, and quick achievable deductions."""
    logger.info("Executing get_tax_planning_insights for %s", user_id)
    txns = fetch_user_transactions(user_id)
    return get_tax_insights(txns)

@tool
def get_user_calendar_deadlines(user_id: str) -> dict:
    """Use this tool to see the user's upcoming compliance and tax deadlines, the forms required, and penalty consequences."""
    logger.info("Executing get_user_calendar_deadlines for %s", user_id)
    return get_compliance_calendar_events(user_id)
