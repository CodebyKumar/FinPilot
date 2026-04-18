from __future__ import annotations

from fastapi import APIRouter, HTTPException

from finpilot.schemas.modules import (
    OverallReportEmailRequest,
    OverallReportGenerateRequest,
    OverallReportPdfRequest,
)
from finpilot.services.overall_report_service import (
    email_overall_report,
    generate_overall_report,
    generate_overall_report_pdf,
    get_overall_report,
)

router = APIRouter(prefix="/overall-report", tags=["Overall Report"])


@router.post("/generate")
def generate_overall_report_route(payload: OverallReportGenerateRequest):
    try:
        data = generate_overall_report(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{report_id}")
def get_overall_report_route(report_id: str, user_id: str):
    try:
        data = get_overall_report(user_id, report_id)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/generate-pdf")
def generate_overall_report_pdf_route(payload: OverallReportPdfRequest):
    try:
        data = generate_overall_report_pdf(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/email")
def email_overall_report_route(payload: OverallReportEmailRequest):
    try:
        data = email_overall_report(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
