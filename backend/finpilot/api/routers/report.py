from __future__ import annotations

import json
import os
import re
import tempfile
from html import escape
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from fastapi import UploadFile, File, Form

from finpilot.schemas.modules import ReportRequest, ReportEmailRequest
from finpilot.services.gmail_service import resolve_user_email, send_email
from finpilot.services.execute_service import (
    report_extract_fields,
    report_generate,
    report_status,
    report_view,
    report_prefill,
    report_analyze,
    report_validate,
)

router = APIRouter(prefix="/report", tags=["Report"])


def _safe_report_filename(report_name: str | None, report_id: str, suffix: str) -> str:
    raw_name = str(report_name or "report").strip().lower()
    safe_name = re.sub(r"[^a-z0-9._-]+", "_", raw_name).strip("_") or "report"
    safe_report_id = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(report_id)).strip("_") or "report"
    return f"{safe_name}_{safe_report_id}.{suffix}"


def _render_value_for_pdf(value: object) -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, (dict, list, tuple, set)):
        try:
            return json.dumps(value, indent=2, default=str)
        except Exception:
            return str(value)
    return str(value)


def _to_pdf_paragraph_text(value: object) -> str:
    text = _render_value_for_pdf(value)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return escape(normalized).replace("\n", "<br/>")


def _build_report_pdf(report_doc: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    story = []

    report_id = str(report_doc.get("report_id") or "-")
    report_name = str(report_doc.get("report_name") or "Tax Report")
    updated_at = str(report_doc.get("updated_at") or report_doc.get("created_at") or "-")

    story.append(Paragraph(report_name, styles["Title"]))
    story.append(Spacer(1, 10))

    summary_rows = [
        ["Report ID", report_id],
        ["User ID", str(report_doc.get("user_id") or "-")],
        ["Updated At", updated_at],
    ]
    summary_table = Table(summary_rows, colWidths=[130, 380])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F4F6")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Extracted / Filled Fields", styles["Heading2"]))
    story.append(Spacer(1, 8))

    fields = report_doc.get("fields") if isinstance(report_doc.get("fields"), list) else []
    if not fields:
        story.append(Paragraph("No fields available for this report.", styles["Normal"]))
    else:
        header_style = ParagraphStyle(
            "ReportTableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.white,
            leading=11,
        )
        cell_style = ParagraphStyle(
            "ReportTableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10.5,
            wordWrap="CJK",
        )

        table_data = [
            [
                Paragraph("Identifier", header_style),
                Paragraph("Field", header_style),
                Paragraph("Value", header_style),
            ]
        ]
        max_rows = 250

        for index, field in enumerate(fields, start=1):
            if not isinstance(field, dict):
                continue
            field_name = field.get("field_name") or field.get("field_id") or "Field"
            identifier = field.get("field_id") or f"Field-{index}"
            table_data.append(
                [
                    Paragraph(_to_pdf_paragraph_text(identifier), cell_style),
                    Paragraph(_to_pdf_paragraph_text(field_name), cell_style),
                    Paragraph(_to_pdf_paragraph_text(field.get("value")), cell_style),
                ]
            )
            if len(table_data) - 1 >= max_rows:
                break

        field_table = Table(table_data, colWidths=[95, 165, 250], repeatRows=1)
        field_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 1), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ]
            )
        )
        story.append(field_table)

        if len(fields) > max_rows:
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Showing first {max_rows} fields.", styles["Italic"]))

    document.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _build_report_email_body(report_doc: dict, report_id: str) -> str:
    report_name = str(report_doc.get("report_name") or "Tax Report")
    generated_at = str(report_doc.get("updated_at") or report_doc.get("created_at") or "-")
    return (
        "Hello,\n\n"
        "Your generated tax report PDF is attached to this email.\n\n"
        f"Report Name: {report_name}\n"
        f"Report ID: {report_id}\n"
        f"Generated At: {generated_at}\n\n"
        "Please review the report and keep this copy for your records.\n\n"
        "Regards,\n"
        "FinPilot"
    )


@router.post("/extract-fields")
def extract_fields_route(payload: ReportRequest):
    try:
        data = report_extract_fields(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/extract-fields-file")
async def extract_fields_file_route(user_id: str = Form(...), file: UploadFile = File(...), report_name: str | None = Form(None)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        payload = {"file_path": tmp_path, "report_name": report_name or "ITR-1"}
        data = report_extract_fields(user_id, payload)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/generate")
def generate_report_route(payload: ReportRequest):
    try:
        data = report_generate(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/generate-file")
async def generate_report_file_route(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    report_name: str | None = Form(None),
    report_id: str | None = Form(None),
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        payload = {"file_path": tmp_path, "report_name": report_name or "ITR-1", "report_id": report_id}
        data = report_generate(user_id, payload)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/status/{report_id}")
def report_status_route(report_id: str, user_id: str):
    try:
        data = report_status(user_id, report_id)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/view/{report_id}")
def report_view_route(report_id: str, user_id: str):
    try:
        data = report_view(user_id, report_id)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/download/{report_id}")
def report_download_route(report_id: str, user_id: str):
    try:
        data = report_view(user_id, report_id)
        if not data.get("found"):
            raise HTTPException(status_code=404, detail=f"Report not found for report_id {report_id}")

        report_doc = data.get("report") if isinstance(data.get("report"), dict) else {}
        filename = _safe_report_filename(report_doc.get("report_name"), report_id, "pdf")
        body = _build_report_pdf(report_doc)

        return Response(
            content=body,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/email")
def email_report_route(payload: ReportEmailRequest):
    try:
        data = report_view(payload.user_id, payload.report_id)
        if not data.get("found"):
            raise HTTPException(status_code=404, detail=f"Report not found for report_id {payload.report_id}")

        report_doc = data.get("report") if isinstance(data.get("report"), dict) else {}
        recipient = resolve_user_email(payload.user_id)
        if not recipient:
            raise HTTPException(
                status_code=400,
                detail="No user email found. Update profile email before sending report.",
            )

        attachment_name = _safe_report_filename(report_doc.get("report_name"), payload.report_id, "pdf")
        attachment_bytes = _build_report_pdf(report_doc)
        email_result = send_email(
            recipient=recipient,
            subject=f"Tax Report - {payload.report_id}",
            body=_build_report_email_body(report_doc, payload.report_id),
            attachments=[(attachment_name, attachment_bytes, "application/pdf")],
        )

        if not email_result.get("sent"):
            raise HTTPException(status_code=502, detail=email_result.get("info") or "Failed to send report email")

        return {
            "success": True,
            "data": {
                "report_id": payload.report_id,
                "recipient": recipient,
                "attachment": attachment_name,
                **email_result,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/prefill/{user_id}")
def report_prefill_route(user_id: str):
    try:
        data = report_prefill(user_id)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/analyze")
def analyze_report_route(payload: ReportRequest):
    try:
        data = report_analyze(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/analyze-file")
async def analyze_report_file_route(user_id: str = Form(...), file: UploadFile = File(...), report_id: str | None = Form(None)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        payload = {"file_path": tmp_path, "report_id": report_id}
        data = report_analyze(user_id, payload)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/validate")
def validate_report_route(payload: ReportRequest):
    try:
        data = report_validate(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
