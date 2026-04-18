from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, HTTPException
from fastapi import UploadFile, File, Form

from finpilot.schemas.modules import ReportRequest
from finpilot.services.execute_service import (
    report_extract_fields,
    report_generate,
    report_status,
    report_analyze,
    report_validate,
)

router = APIRouter(prefix="/report", tags=["Report"])


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
        payload = {"file_path": tmp_path, "report_name": report_name}
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
        payload = {"file_path": tmp_path, "report_name": report_name, "report_id": report_id}
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
