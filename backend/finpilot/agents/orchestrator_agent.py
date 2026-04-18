from __future__ import annotations

from copy import deepcopy
import json
import re
from datetime import datetime, timedelta
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from finpilot import config
from finpilot.api.deps import fetch_user_transactions
from finpilot.db.mongo import (
    _get_db,
    get_agent_memories_collection,
    get_assistant_chat_history_collection,
    get_user,
)
from finpilot.tools.compliance_tools import query_deadlines_data
from finpilot.tools.finance_tools import query_bookkeeping_data
from finpilot.tools.report_tools import plan_report_assist_data
from finpilot.utils.profile_security import decrypt_sensitive_value, mask_sensitive_value


class State(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    user_profile: dict[str, Any]
    transactions: list[Any]
    memory_highlights: list[dict[str, Any]]
    capability: str
    capability_payload: dict[str, Any]
    capability_result: dict[str, Any]


BOOKKEEPING_KEYWORDS = {
    "bookkeeping",
    "ledger",
    "transaction",
    "transactions",
    "expense",
    "expenses",
    "profit",
    "cashflow",
    "cash flow",
    "reconciliation",
    "gst",
    "itc",
}

DEADLINE_KEYWORDS = {
    "deadline",
    "deadlines",
    "due",
    "due date",
    "compliance calendar",
    "reminder",
    "reminders",
    "overdue",
    "filing date",
}

REPORT_KEYWORDS = {
    "report",
    "reports",
    "itr",
    "itr-1",
    "return filing",
    "tax form",
    "form",
    "prefill",
    "fill form",
    "upload form",
}

SENSITIVE_PROFILE_FIELDS = {"pan", "aadhaar"}


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _mask_sensitive_profile(profile_doc: dict[str, Any]) -> dict[str, Any]:
    masked = deepcopy(profile_doc)

    personal = masked.get("personal_info") if isinstance(masked.get("personal_info"), dict) else {}
    for key in SENSITIVE_PROFILE_FIELDS:
        if key in personal:
            decrypted = decrypt_sensitive_value(personal.get(key))
            personal[key] = mask_sensitive_value(decrypted)

    bank_accounts = masked.get("bank_accounts")
    if isinstance(bank_accounts, list):
        for account in bank_accounts:
            if not isinstance(account, dict):
                continue
            account_number = account.get("account_number")
            if account_number is None:
                continue
            account["account_number"] = mask_sensitive_value(str(account_number), prefix=2, suffix=2)

    return masked


def _load_user_profile_bundle(user_id: str) -> dict[str, Any]:
    user_doc = get_user(user_id) or {}

    profile_doc = _get_db()["profiles"].find_one(
        {"user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0},
    ) or {}
    if not isinstance(profile_doc, dict):
        profile_doc = {}

    masked_profile = _mask_sensitive_profile(profile_doc)
    return {
        "user": user_doc,
        "profile": masked_profile,
    }


def _build_profile_context_for_prompt(profile_bundle: dict[str, Any]) -> dict[str, Any]:
    user_doc = profile_bundle.get("user") if isinstance(profile_bundle.get("user"), dict) else {}
    profile_doc = profile_bundle.get("profile") if isinstance(profile_bundle.get("profile"), dict) else {}

    personal = profile_doc.get("personal_info") if isinstance(profile_doc.get("personal_info"), dict) else {}
    business = profile_doc.get("business_info") if isinstance(profile_doc.get("business_info"), dict) else {}
    tax_preferences = profile_doc.get("tax_preferences") if isinstance(profile_doc.get("tax_preferences"), dict) else {}
    income_sources = profile_doc.get("income_sources") if isinstance(profile_doc.get("income_sources"), list) else []
    bank_accounts = profile_doc.get("bank_accounts") if isinstance(profile_doc.get("bank_accounts"), list) else []

    return {
        "name": personal.get("full_name") or user_doc.get("name"),
        "phone": personal.get("phone") or user_doc.get("phone"),
        "email": personal.get("email"),
        "business_name": business.get("business_name") or user_doc.get("business_name"),
        "industry": business.get("industry") or user_doc.get("industry"),
        "entity_type": business.get("entity_type") or user_doc.get("entity_type"),
        "annual_turnover": _safe_number(
            user_doc.get("annual_turnover")
            if user_doc.get("annual_turnover") not in (None, "")
            else business.get("annual_turnover"),
            0.0,
        ),
        "income_sources": income_sources[:10],
        "tax_preferences": tax_preferences,
        "bank_accounts": bank_accounts[:3],
    }


def _now_iso() -> str:
    return datetime.now().isoformat()


def _safe_message_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        try:
            return json.dumps(value, default=str)
        except Exception:
            return str(value)
    return str(value).strip()


def _latest_user_message(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return _safe_message_text(message.content)
    return ""


def _chat_history_collection():
    return get_assistant_chat_history_collection()


def _agent_memory_collection():
    return get_agent_memories_collection()


def _load_recent_chat_messages(user_id: str, max_messages: int) -> list[BaseMessage]:
    docs = list(
        _chat_history_collection()
        .find({"user_id": user_id}, {"_id": 0, "role": 1, "content": 1})
        .sort("created_at", -1)
        .limit(max(0, max_messages))
    )
    docs.reverse()

    restored: list[BaseMessage] = []
    for doc in docs:
        role = str(doc.get("role", "user")).lower().strip()
        content = _safe_message_text(doc.get("content"))
        if not content:
            continue
        if role == "assistant":
            restored.append(AIMessage(content=content))
        elif role == "system":
            restored.append(SystemMessage(content=content))
        else:
            restored.append(HumanMessage(content=content))
    return restored


def _load_memory_highlights(user_id: str, max_items: int) -> list[dict[str, Any]]:
    docs = list(
        _agent_memory_collection()
        .find({"user_id": user_id}, {"_id": 0, "capability": 1, "highlights": 1, "updated_at": 1})
        .sort("updated_at", -1)
        .limit(max(0, max_items))
    )
    highlights: list[dict[str, Any]] = []
    for doc in docs:
        line_items = doc.get("highlights") if isinstance(doc.get("highlights"), list) else []
        joined = "; ".join(str(item).strip() for item in line_items if str(item).strip())
        if not joined:
            continue
        highlights.append(
            {
                "capability": doc.get("capability", "general"),
                "summary": joined,
                "updated_at": doc.get("updated_at"),
            }
        )
    return highlights


def _persist_chat_turn(user_id: str, user_message: str, assistant_message: str, capability: str) -> None:
    created_at = _now_iso()
    _chat_history_collection().insert_many(
        [
            {
                "user_id": user_id,
                "role": "user",
                "content": user_message,
                "capability": capability,
                "created_at": created_at,
            },
            {
                "user_id": user_id,
                "role": "assistant",
                "content": assistant_message,
                "capability": capability,
                "created_at": created_at,
            },
        ]
    )


def _extract_memory_highlights(capability: str, capability_result: dict[str, Any]) -> list[str]:
    data = capability_result.get("result") if isinstance(capability_result, dict) else {}
    if not isinstance(data, dict):
        return []

    if capability == "bookkeeping":
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
        return [
            f"Net cash flow: {summary.get('net_cash_flow', 0)}",
            f"Credits: {summary.get('total_credits', 0)}",
            f"Debits: {summary.get('total_debits', 0)}",
        ]

    if capability == "deadline":
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
        return [
            f"Pending deadlines: {summary.get('pending', 0)}",
            f"Overdue deadlines: {summary.get('overdue', 0)}",
            f"Upcoming deadlines: {summary.get('upcoming_within_window', 0)}",
        ]

    if capability == "report":
        return [
            f"Selected form: {data.get('selected_form', 'ITR-1')}",
            f"Readiness score: {data.get('readiness_score', 0)}",
            f"Upload target: {data.get('upload_target', 'internal_platform')}",
        ]

    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    if summary:
        return [f"General summary keys: {', '.join(summary.keys())}"]
    return []


def _remember_capability_result(user_id: str, capability: str, capability_result: dict[str, Any]) -> None:
    highlights = [item for item in _extract_memory_highlights(capability, capability_result) if item]
    if not highlights:
        return

    timestamp = _now_iso()
    _agent_memory_collection().insert_one(
        {
            "user_id": user_id,
            "capability": capability,
            "highlights": highlights,
            "updated_at": timestamp,
        }
    )


def _infer_bookkeeping_payload(user_query: str) -> dict[str, Any]:
    lowered = user_query.lower()
    query_type = "summary_metrics"
    filters: dict[str, Any] = {}
    limit = 100

    detail_terms = {
        "transaction",
        "transactions",
        "entry",
        "entries",
        "record",
        "records",
        "correction",
        "corrections",
    }
    summary_terms = {
        "summary",
        "overall",
        "total",
        "totals",
        "net",
        "insight",
        "analysis",
        "trend",
        "trends",
    }

    limit_match = re.search(
        r"(?:last|recent|latest|top|first)\s+(\d{1,3})\s+(?:transactions?|entries?|records?|corrections?)",
        lowered,
    )
    if limit_match:
        limit = max(1, min(int(limit_match.group(1)), 200))
        query_type = "full_ledger"

    if "ledger" in lowered or "all transaction" in lowered or "book of transaction" in lowered:
        query_type = "full_ledger"
    elif any(term in lowered for term in detail_terms) and not any(term in lowered for term in summary_terms):
        query_type = "full_ledger"
        if limit_match is None:
            limit = 20
    elif "category" in lowered:
        query_type = "by_category"
    elif "anomaly" in lowered or "outlier" in lowered or "unusual" in lowered:
        query_type = "anomalies"
    elif "gst" in lowered or "itc" in lowered:
        query_type = "gst_analysis"

    days_match = re.search(r"last\s+(\d{1,3})\s+day", lowered)
    if days_match:
        days = int(days_match.group(1))
        date_from = (datetime.now() - timedelta(days=max(1, min(days, 3650)))).date().isoformat()
        filters["date_from"] = date_from

    if "this month" in lowered:
        month_start = datetime.now().replace(day=1).date().isoformat()
        filters["date_from"] = month_start

    if "business" in lowered and "personal" not in lowered:
        filters["business_nature"] = "business"
    if "personal" in lowered and "business" not in lowered:
        filters["business_nature"] = "personal"

    return {"query_type": query_type, "filters": filters, "limit": limit}


def _infer_deadline_payload(user_query: str) -> dict[str, Any]:
    lowered = user_query.lower()
    filter_by = "all"
    if any(token in lowered for token in ("pending", "upcoming", "next", "soon")):
        filter_by = "pending"
    if any(token in lowered for token in ("overdue", "missed", "late")):
        filter_by = "overdue"

    deadline_type = "all"
    if "gst" in lowered:
        deadline_type = "gst"
    elif "tax" in lowered or "itr" in lowered:
        deadline_type = "tax"
    elif "audit" in lowered:
        deadline_type = "audit"
    elif "payment" in lowered or "invoice" in lowered:
        deadline_type = "payment"

    window_days = 45
    if "this week" in lowered:
        window_days = 7
    elif "this month" in lowered:
        window_days = 31

    return {
        "filter_by": filter_by,
        "deadline_type": deadline_type,
        "window_days": window_days,
        "include_calendar": True,
    }


def _requested_transaction_limit(user_query: str) -> int | None:
    lowered = user_query.lower()
    match = re.search(
        r"(?:last|recent|latest|top|first)\s+(\d{1,3})\s+(?:transactions?|entries?|records?|corrections?)",
        lowered,
    )
    if not match:
        return None
    return max(1, min(int(match.group(1)), 200))


def _maybe_direct_bookkeeping_response(user_query: str, capability_result: dict[str, Any]) -> str | None:
    if not isinstance(capability_result, dict):
        return None

    result_payload = capability_result.get("result")
    result = result_payload if isinstance(result_payload, dict) else capability_result
    if not isinstance(result, dict):
        return None

    entries = result.get("entries")
    if not isinstance(entries, list) or not entries:
        return None

    lowered = user_query.lower()
    detail_tokens = ("transaction", "transactions", "entry", "entries", "record", "records", "correction", "corrections")
    if not any(token in lowered for token in detail_tokens):
        return None

    requested_limit = _requested_transaction_limit(user_query) or 10
    selected = entries[: max(1, min(requested_limit, len(entries)))]

    lines: list[str] = [f"Here are your last {len(selected)} transactions:"]
    for item in selected:
        if not isinstance(item, dict):
            continue

        date = str(item.get("date") or "-")
        party = str(item.get("party") or "Unknown")
        txn_type = str(item.get("type") or "-").upper()
        amount_raw = item.get("amount")
        try:
            amount_text = f"INR {float(amount_raw):,.2f}"
        except Exception:
            amount_text = f"INR {amount_raw}"

        lines.append(f"- {date}: {party} ({txn_type}) - {amount_text}")

    total_after_filter = result.get("total_after_filter")
    if isinstance(total_after_filter, int) and total_after_filter > len(selected):
        lines.append(f"Showing {len(selected)} of {total_after_filter} matching transactions.")

    return "\n".join(lines)


def load_context(state: State) -> dict[str, Any]:
    user_id = state.get("user_id", "")
    return {
        "transactions": fetch_user_transactions(user_id),
        "memory_highlights": _load_memory_highlights(
            user_id,
            max_items=getattr(config, "AGENT_MEMORY_MAX_HIGHLIGHTS", 8),
        ),
    }


def load_profile_context(state: State) -> dict[str, Any]:
    user_id = state.get("user_id", "")
    return {"user_profile": _load_user_profile_bundle(user_id)}


def route_capability(state: State) -> dict[str, Any]:
    user_query = _latest_user_message(state.get("messages", []))
    lowered = user_query.lower()

    capability = "general"
    payload: dict[str, Any] = {}

    if any(keyword in lowered for keyword in REPORT_KEYWORDS):
        capability = "report"
        payload = {
            "user_query": user_query,
            "include_prefill": True,
            "auto_generate": any(keyword in lowered for keyword in ("generate", "create report", "draft")),
        }
    elif any(keyword in lowered for keyword in DEADLINE_KEYWORDS):
        capability = "deadline"
        payload = _infer_deadline_payload(user_query)
    elif any(keyword in lowered for keyword in BOOKKEEPING_KEYWORDS):
        capability = "bookkeeping"
        payload = _infer_bookkeeping_payload(user_query)

    return {"capability": capability, "capability_payload": payload}


def run_bookkeeping_capability(state: State) -> dict[str, Any]:
    payload = state.get("capability_payload", {})
    result = query_bookkeeping_data(
        user_id=state.get("user_id", ""),
        query_type=str(payload.get("query_type", "summary_metrics")),
        filters=payload.get("filters") if isinstance(payload.get("filters"), dict) else {},
        limit=int(payload.get("limit", 100)),
        transactions=state.get("transactions"),
    )
    return {"capability_result": {"capability": "bookkeeping", "result": result}}


def run_deadline_capability(state: State) -> dict[str, Any]:
    payload = state.get("capability_payload", {})
    result = query_deadlines_data(
        user_id=state.get("user_id", ""),
        filter_by=str(payload.get("filter_by", "all")),
        deadline_type=str(payload.get("deadline_type", "all")),
        window_days=int(payload.get("window_days", 45)),
        include_calendar=bool(payload.get("include_calendar", True)),
    )
    return {"capability_result": {"capability": "deadline", "result": result}}


def run_report_capability(state: State) -> dict[str, Any]:
    payload = state.get("capability_payload", {})
    result = plan_report_assist_data(
        user_id=state.get("user_id", ""),
        user_query=str(payload.get("user_query", "")),
        include_prefill=bool(payload.get("include_prefill", True)),
        auto_generate=bool(payload.get("auto_generate", False)),
    )
    return {"capability_result": {"capability": "report", "result": result}}


def run_general_capability(state: State) -> dict[str, Any]:
    user_id = state.get("user_id", "")
    quick_summary = query_bookkeeping_data(
        user_id=user_id,
        query_type="summary_metrics",
        filters={},
        limit=20,
        transactions=state.get("transactions"),
    )
    deadline_summary = query_deadlines_data(
        user_id=user_id,
        filter_by="pending",
        deadline_type="all",
        window_days=30,
        include_calendar=False,
    )

    return {
        "capability_result": {
            "capability": "general",
            "result": {
                "summary": {
                    "bookkeeping": quick_summary.get("summary", {}),
                    "deadlines": deadline_summary.get("summary", {}),
                },
                "note": "General route used because no single specialist capability was a clear match.",
            },
        }
    }


ORCHESTRATOR_MODEL = getattr(config, "ORCHESTRATOR_OPENAI_MODEL", "gpt-4o") or "gpt-4o"
llm = ChatOpenAI(model=ORCHESTRATOR_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.1)


def synthesize_response(state: State) -> dict[str, Any]:
    messages = state.get("messages", [])
    user_query = _latest_user_message(messages)
    profile_bundle = state.get("user_profile", {}) if isinstance(state.get("user_profile"), dict) else {}
    user_doc = profile_bundle.get("user") if isinstance(profile_bundle.get("user"), dict) else {}
    profile_doc = profile_bundle.get("profile") if isinstance(profile_bundle.get("profile"), dict) else {}
    capability = state.get("capability", "general")
    capability_result = state.get("capability_result", {})
    memory_highlights = state.get("memory_highlights", [])

    result_payload = capability_result.get("result") if isinstance(capability_result, dict) else {}
    if not isinstance(result_payload, dict):
        result_payload = capability_result if isinstance(capability_result, dict) else {}
    query_type = str(result_payload.get("query_type", "")).strip().lower()

    memory_lines = []
    for item in memory_highlights[:5]:
        capability_name = str(item.get("capability", "general"))
        summary = str(item.get("summary", "")).strip()
        if summary:
            memory_lines.append(f"- {capability_name}: {summary}")

    context_payload = {
        "capability": capability,
        "capability_result": capability_result,
        "memory_highlights": memory_lines,
        "query_type": query_type,
        "profile_context": _build_profile_context_for_prompt(profile_bundle),
    }

    business = profile_doc.get("business_info") if isinstance(profile_doc.get("business_info"), dict) else {}
    industry = user_doc.get("industry") or business.get("industry") or "Unknown"
    entity_type = user_doc.get("entity_type") or business.get("entity_type") or "Unknown"
    turnover = _safe_number(
        user_doc.get("annual_turnover")
        if user_doc.get("annual_turnover") not in (None, "")
        else business.get("annual_turnover"),
        0.0,
    )

    system_prompt = (
        "You are FinPilot Orchestrator V1, a multi-agent financial assistant. "
        "Respond with clear, practical financial guidance grounded in the structured capability output. "
        "Use conversation history to resolve follow-up references like 'that', 'previous', and 'same as before'. "
        "When query_type is full_ledger and entries are present, list concrete entries from the tool data rather than only summaries. "
        "If user action is needed, provide concise next steps. "
        "Do not fabricate values that are missing from capability_result.\n"
        f"Business context:\n- Industry: {industry}\n- Entity: {entity_type}\n- Turnover: INR {turnover:,.2f}\n"
    )

    model_messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
    context_window = getattr(config, "AGENT_MEMORY_MAX_HISTORY_MESSAGES", 12)
    try:
        context_window = max(4, min(int(context_window), 24))
    except Exception:
        context_window = 12
    model_messages.extend(messages[-context_window:])
    model_messages.append(
        HumanMessage(
            content=(
                f"User query: {user_query}\n"
                "Structured orchestrator context (JSON):\n"
                f"{json.dumps(context_payload, default=str)[:15000]}"
            )
        )
    )

    response = llm.invoke(model_messages)
    return {"messages": [response]}


def _route_edge(state: State) -> str:
    capability = state.get("capability", "general")
    if capability == "bookkeeping":
        return "bookkeeping"
    if capability == "deadline":
        return "deadline"
    if capability == "report":
        return "report"
    return "general"


workflow = StateGraph(State)
workflow.add_node("load_context", load_context)
workflow.add_node("load_profile_context", load_profile_context)
workflow.add_node("route_capability", route_capability)
workflow.add_node("bookkeeping_capability", run_bookkeeping_capability)
workflow.add_node("deadline_capability", run_deadline_capability)
workflow.add_node("report_capability", run_report_capability)
workflow.add_node("general_capability", run_general_capability)
workflow.add_node("synthesize_response", synthesize_response)

workflow.add_edge(START, "load_context")
workflow.add_edge("load_context", "load_profile_context")
workflow.add_edge("load_profile_context", "route_capability")
workflow.add_conditional_edges(
    "route_capability",
    _route_edge,
    {
        "bookkeeping": "bookkeeping_capability",
        "deadline": "deadline_capability",
        "report": "report_capability",
        "general": "general_capability",
    },
)
workflow.add_edge("bookkeeping_capability", "synthesize_response")
workflow.add_edge("deadline_capability", "synthesize_response")
workflow.add_edge("report_capability", "synthesize_response")
workflow.add_edge("general_capability", "synthesize_response")
workflow.add_edge("synthesize_response", END)

app = workflow.compile()


def get_orchestrator_graph_mermaid() -> str:
    try:
        return app.get_graph().draw_mermaid()
    except Exception:
        return (
            "flowchart TD\n"
            "    START --> load_context\n"
            "    load_context --> load_profile_context\n"
            "    load_profile_context --> route_capability\n"
            "    route_capability --> bookkeeping_capability\n"
            "    route_capability --> deadline_capability\n"
            "    route_capability --> report_capability\n"
            "    route_capability --> general_capability\n"
            "    bookkeeping_capability --> synthesize_response\n"
            "    deadline_capability --> synthesize_response\n"
            "    report_capability --> synthesize_response\n"
            "    general_capability --> synthesize_response\n"
            "    synthesize_response --> END"
        )


def get_orchestrator_graph_metadata() -> dict[str, Any]:
    return {
        "version": "v1",
        "nodes": [
            "load_context",
            "load_profile_context",
            "route_capability",
            "bookkeeping_capability",
            "deadline_capability",
            "report_capability",
            "general_capability",
            "synthesize_response",
        ],
        "routes": ["bookkeeping", "deadline", "report", "general"],
    }


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _build_execution_trace(capability: str, capability_result: dict[str, Any]) -> dict[str, Any]:
    result_payload = capability_result.get("result") if isinstance(capability_result, dict) else {}
    if not isinstance(result_payload, dict):
        result_payload = capability_result if isinstance(capability_result, dict) else {}

    route = str(capability or "general")
    agents_used = [f"{route}_capability", "synthesize_response"]
    resources_used: list[str]

    if route == "bookkeeping":
        resources_used = ["transactions", "bookkeeping_entries"]
        if result_payload.get("query_type") == "gst_analysis":
            resources_used.append("gst_rules")
    elif route == "deadline":
        resources_used = ["deadlines"]
        if isinstance(result_payload.get("calendar_events"), list):
            resources_used.append("compliance_calendar")
    elif route == "report":
        resources_used = ["profiles", "reports", "transactions"]
        if isinstance(result_payload.get("prefill"), dict):
            resources_used.append("prefill_profile_mapping")
    else:
        resources_used = ["transactions", "deadlines"]

    trace: dict[str, Any] = {
        "route": route,
        "agents_used": _dedupe_strings(agents_used),
        "resources_used": _dedupe_strings(resources_used),
    }

    query_type = result_payload.get("query_type")
    if isinstance(query_type, str) and query_type.strip():
        trace["query_type"] = query_type.strip()

    return trace


def execute_goal(user_id: str, message: str) -> dict[str, Any]:
    user_text = _safe_message_text(message)
    if not user_text:
        return {
            "user_id": user_id,
            "input_query": message,
            "agent_response": "Please share a valid question.",
            "capability": "general",
        }

    history = _load_recent_chat_messages(
        user_id,
        max_messages=getattr(config, "AGENT_MEMORY_MAX_HISTORY_MESSAGES", 12),
    )

    final_state = app.invoke(
        {
            "messages": [*history, HumanMessage(content=user_text)],
            "user_id": user_id,
        }
    )

    response_message = final_state.get("messages", [AIMessage(content="")])[-1]
    assistant_text = _safe_message_text(getattr(response_message, "content", ""))
    capability = str(final_state.get("capability", "general"))
    capability_result = final_state.get("capability_result", {})
    trace = _build_execution_trace(capability, capability_result if isinstance(capability_result, dict) else {})

    _persist_chat_turn(user_id, user_text, assistant_text, capability)
    if isinstance(capability_result, dict):
        _remember_capability_result(user_id, capability, capability_result)

    return {
        "user_id": user_id,
        "input_query": user_text,
        "agent_response": assistant_text,
        "capability": capability,
        "capability_result": capability_result,
        "trace": trace,
    }
