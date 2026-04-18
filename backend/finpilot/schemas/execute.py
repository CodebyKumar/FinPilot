from __future__ import annotations

from typing import Any, Literal
from enum import Enum

from pydantic import BaseModel, Field


class ExecuteMode(str, Enum):
    sync = "sync"
    async_mode = "async"


class TaskName(str, Enum):
    create_profile = "create_profile"
    get_profile = "get_profile"
    update_profile = "update_profile"
    delete_profile = "delete_profile"
    bookkeeping_upload_statement = "bookkeeping_upload_statement"
    bookkeeping_upload_invoice = "bookkeeping_upload_invoice"
    bookkeeping_add_entry = "bookkeeping_add_entry"
    bookkeeping_update_entry = "bookkeeping_update_entry"
    bookkeeping_get_ledger = "bookkeeping_get_ledger"
    report_extract_fields = "report_extract_fields"
    report_generate = "report_generate"
    report_status = "report_status"
    report_analyze = "report_analyze"
    report_validate = "report_validate"
    deadline_add = "deadline_add"
    deadline_get = "deadline_get"
    deadline_delete = "deadline_delete"
    assistant_chat = "assistant_chat"


class ExecuteRequest(BaseModel):
    task_name: TaskName
    user_id: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    mode: ExecuteMode = ExecuteMode.sync
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)


class ExecuteResponse(BaseModel):
    status: Literal["success", "accepted", "error"]
    task_name: str
    user_id: str
    data: Any | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    correlation_id: str
    job_id: str | None = None


class JobStatusResponse(BaseModel):
    found: bool
    job_id: str | None = None
    job: dict[str, Any] | None = None
