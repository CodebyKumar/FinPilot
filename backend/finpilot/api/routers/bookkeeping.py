from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from finpilot.schemas.modules import (
    BookkeepingAddEntryRequest,
    BookkeepingUpdateEntryRequest,
    BookkeepingUploadInvoiceRequest,
)
from finpilot.services.execute_service import (
    bookkeeping_add_entry,
    bookkeeping_get_ledger,
    bookkeeping_update_entry,
    bookkeeping_upload_statement_from_path,
    bookkeeping_upload_invoice,
)

router = APIRouter(prefix="/bookkeeping", tags=["Bookkeeping"])


@router.post("/upload-statement")
async def upload_statement_route(user_id: str = Form(...), file: UploadFile = File(...)):
    suffix = Path(file.filename or "statement.pdf").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        data = bookkeeping_upload_statement_from_path(user_id, tmp_path)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/add-entry")
def add_entry_route(payload: BookkeepingAddEntryRequest):
    try:
        data = bookkeeping_add_entry(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload-invoice")
def upload_invoice_route(payload: BookkeepingUploadInvoiceRequest):
    try:
        data = bookkeeping_upload_invoice(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload-invoice-file")
async def upload_invoice_file_route(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    party: str | None = Form(None),
    amount: float | None = Form(None),
    date: str | None = Form(None),
    notes: str = Form(""),
):
    backend_root = Path(__file__).resolve().parents[4]
    uploads_dir = backend_root / "data" / "uploads" / "invoices"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "invoice.pdf").suffix or ".pdf"
    target_path = uploads_dir / f"{uuid4().hex}{suffix}"

    with open(target_path, "wb") as f:
        f.write(await file.read())

    payload = {
        "file_path": str(target_path),
        "party": party,
        "amount": amount,
        "date": date,
        "notes": notes,
    }

    try:
        data = bookkeeping_upload_invoice(user_id, payload)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/ledger/{user_id}")
def ledger_route(user_id: str):
    try:
        data = bookkeeping_get_ledger(user_id)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update-entry/{entry_id}")
def update_entry_route(entry_id: str, payload: BookkeepingUpdateEntryRequest):
    try:
        data = bookkeeping_update_entry(payload.user_id, entry_id, payload.updates)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
