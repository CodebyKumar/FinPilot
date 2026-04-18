from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from langchain_core.tools import tool


def _normalize_income_sources(profile: dict[str, Any]) -> list[str]:
    sources = profile.get("income_sources", []) if isinstance(profile, dict) else []
    normalized: list[str] = []
    for source in sources:
        if isinstance(source, dict):
            name = source.get("type") or source.get("name") or source.get("source")
            if name:
                normalized.append(str(name).strip().lower())
        elif isinstance(source, str):
            normalized.append(source.strip().lower())
    return [item for item in normalized if item]


def _select_form(profile: dict[str, Any], user_query: str) -> tuple[str, list[str], float, str]:
    personal_info = profile.get("personal_info", {}) if isinstance(profile, dict) else {}
    business_info = profile.get("business_info", {}) if isinstance(profile, dict) else {}
    entity_type = str(
        business_info.get("entity_type")
        or business_info.get("entity")
        or personal_info.get("entity_type")
        or "individual"
    ).strip().lower()

    income_sources = _normalize_income_sources(profile)
    query = (user_query or "").lower()

    selected_form = "ITR-1"
    alternatives: list[str] = ["ITR-2", "ITR-3", "ITR-4"]
    confidence = 0.72
    rationale = "Defaulted to ITR-1 because dynamic multi-form filing is still rolling out in this backend."

    if "capital" in query or "capital" in " ".join(income_sources):
        selected_form = "ITR-2"
        confidence = 0.68
        rationale = "Detected capital-gains-like context, so ITR-2 is likely relevant."
    elif any(token in query for token in ("business income", "proprietor", "professional", "freelance")):
        selected_form = "ITR-3"
        confidence = 0.66
        rationale = "Detected business/professional income context, so ITR-3 may be required."
    elif "presumptive" in query:
        selected_form = "ITR-4"
        confidence = 0.64
        rationale = "Detected presumptive taxation context, so ITR-4 may be applicable."
    elif entity_type in {"individual", "salaried", "salary"}:
        selected_form = "ITR-1"
        confidence = 0.8
        rationale = "Profile suggests individual/salaried filing path, so ITR-1 is selected."

    alternatives = [form for form in alternatives if form != selected_form]
    return selected_form, alternatives, confidence, rationale


def plan_report_assist_data(
    user_id: str,
    user_query: str = "",
    include_prefill: bool = True,
    auto_generate: bool = False,
) -> Dict[str, Any]:
    # Local imports avoid circular import with execute_service -> orchestrator -> tools chain.
    from finpilot.services.execute_service import get_profile, report_generate, report_prefill

    profile_payload = get_profile(user_id)
    profile = profile_payload.get("profile", {}) if isinstance(profile_payload, dict) else {}

    selected_form, alternatives, confidence, rationale = _select_form(profile, user_query)

    prefill: dict[str, Any] = {}
    if include_prefill:
        try:
            prefill = report_prefill(user_id)
        except Exception as exc:
            prefill = {
                "report_name": selected_form,
                "fields": [],
                "missing_fields": [],
                "error": str(exc),
            }

    generated: dict[str, Any] | None = None
    if auto_generate:
        try:
            generated = report_generate(user_id, {"report_name": selected_form})
        except Exception as exc:
            generated = {"status": "error", "error": str(exc), "report_name": selected_form}

    missing_fields = prefill.get("missing_fields", []) if isinstance(prefill, dict) else []
    missing_count = len(missing_fields) if isinstance(missing_fields, list) else 0
    prefill_fields = prefill.get("prefill_fields", []) if isinstance(prefill, dict) else []
    prefill_count = len(prefill_fields) if isinstance(prefill_fields, list) else 0

    readiness_score = 0
    if prefill_count + missing_count > 0:
        readiness_score = round((prefill_count / max(prefill_count + missing_count, 1)) * 100, 2)

    next_steps = [
        "Review selected form and confirm filing context.",
        "Complete missing mandatory fields in parallel sections.",
        "Generate draft report on internal platform for validation.",
        "Resolve validation warnings before final submission.",
    ]

    response: Dict[str, Any] = {
        "user_id": user_id,
        "selected_form": selected_form,
        "alternatives": alternatives,
        "confidence": confidence,
        "reasoning": rationale,
        "upload_target": "internal_platform",
        "readiness_score": readiness_score,
        "parallel_sections": ["Part A", "Part B", "Schedules"],
        "missing_fields_count": missing_count,
        "missing_fields_preview": missing_fields[:15] if isinstance(missing_fields, list) else [],
        "next_steps": next_steps,
        "generated_at": datetime.now().isoformat(),
    }

    if include_prefill:
        response["prefill"] = {
            "report_name": prefill.get("report_name", selected_form) if isinstance(prefill, dict) else selected_form,
            "missing_fields_count": missing_count,
            "required_user_inputs": prefill.get("required_user_inputs", []) if isinstance(prefill, dict) else [],
        }

    if generated is not None:
        response["generated"] = generated

    return response


@tool
def plan_report_assist(user_id: str, user_query: str = "") -> Dict[str, Any]:
    """Plan the best report/form flow for a user and provide prefill-readiness insights."""
    return plan_report_assist_data(
        user_id=user_id,
        user_query=user_query,
        include_prefill=True,
        auto_generate=False,
    )


@tool
def prepare_report_draft(user_id: str, report_name: str = "ITR-1") -> Dict[str, Any]:
    """Generate a report draft on the internal platform using current profile and ledger context."""
    # Local import avoids circular import at module import time.
    from finpilot.services.execute_service import report_generate

    return report_generate(user_id, {"report_name": report_name})
