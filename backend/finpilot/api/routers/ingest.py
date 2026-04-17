"""
Ingestion Router – PDF uploads
"""

import os
import tempfile

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from finpilot.ingestion import ingest_pdf

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/pdf")
async def ingest_pdf_route(user_id: str = Form(...), file: UploadFile = File(...)):
    """
    Upload a bank statement PDF. Extracts all tabular data natively.
    """
    # Create isolated secure temporary container for file processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        transactions = ingest_pdf(tmp_path, user_id)
        return {
            "transactions": [t.to_dict() for t in transactions],
            "count": len(transactions),
        }
    finally:
        # Guarantee cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
