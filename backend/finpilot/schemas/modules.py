from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ProfileBase(BaseModel):
    personal_info: dict[str, Any] = Field(default_factory=dict)
    business_info: dict[str, Any] = Field(default_factory=dict)
    income_sources: list[dict[str, Any] | str] = Field(default_factory=list)
    bank_accounts: list[dict[str, Any] | str] = Field(default_factory=list)
    tax_preferences: dict[str, Any] = Field(default_factory=dict)


class ProfileCreateRequest(ProfileBase):
    user_id: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(ProfileBase):
    user_id: str = Field(min_length=1, max_length=128)


class BookkeepingAddEntryRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    amount: float
    type: Literal["credit", "debit"] = "debit"
    party: str = "Unknown"
    date: str | None = None
    source: Literal["sms", "pdf", "ocr", "voice"] = "ocr"
    raw_text: str = "manual-entry"
    category: str = "Uncategorized"
    sub_category: str = "Uncategorized"
    business_nature: str = "business"
    gst_rate: float = 0.0
    itc_eligible: bool = False
    hsn_sac: str = "UNKNOWN"
    gst_amount: float = 0.0
    itc_amount: float = 0.0
    matched_rule: str = "manual"
    confidence: float = 1.0


class BookkeepingUpdateEntryRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    updates: dict[str, Any] = Field(default_factory=dict)


class BookkeepingUploadInvoiceRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    invoice_id: str | None = None
    file_path: str | None = None
    amount: float = 0.0
    date: str | None = None
    party: str = "Unknown"
    linked_transaction_id: str | None = None
    notes: str = ""


class ReportRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    report_id: str | None = None
    report_name: str | None = None
    file_path: str | None = None
    report_template_text: str | None = None
    fields: list[dict[str, Any] | str] = Field(default_factory=list)


class ReportEmailRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    report_id: str = Field(min_length=1)


class OverallReportGenerateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    report_id: str | None = None
    report_name: str | None = "Overall Financial Report"
    expected_balance: float | None = None


class OverallReportPdfRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    report_id: str | None = None
    report_name: str | None = "Overall Financial Report"
    expected_balance: float | None = None
    output_dir: str | None = None


class OverallReportEmailRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    report_id: str
    email: str | None = None
    attach_pdf: bool = True
    output_dir: str | None = None


class DeadlineAddRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    deadline_id: str | None = None
    type: str = "compliance"
    title: str = "Compliance deadline"
    due_date: str
    status: str = "pending"
    submitted: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class AssistantChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1)
