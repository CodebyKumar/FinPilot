from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4
from typing import Any

from finpilot import config
from finpilot.api.deps import fetch_user_transactions
from finpilot.agents.bookkeeping_agent import get_bookkeeping_summary
from finpilot.agents.expense_agent import get_expense_summary
from finpilot.agents.profit_agent import get_profit_summary
from finpilot.agents.reconciliation_agent import get_reconciliation_report
from finpilot.agents.tax_savings_agent import get_tax_insights
from finpilot.db.mongo import _get_db
from finpilot.services.gmail_service import resolve_user_email, send_email


def _now_iso() -> str:
    return datetime.now().isoformat()


def _overall_reports_collection():
    return _get_db()["overall_reports"]


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _fmt_inr(value: Any) -> str:
    return f"INR {_safe_float(value):,.2f}"


def _build_action_items(
    bookkeeping_summary: dict[str, Any],
    tax_insights: dict[str, Any],
    reconciliation_report: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    balance_summary = bookkeeping_summary.get("balance_summary", {})
    for suggestion in balance_summary.get("suggestions", []):
        if not isinstance(suggestion, dict):
            continue
        items.append(
            {
                "priority": "medium",
                "title": "Bookkeeping Classification",
                "message": suggestion.get("message", "Review uncategorized transactions."),
            }
        )

    full_plan = tax_insights.get("full_plan", {})
    for rec in full_plan.get("expense_gaps", [])[:5]:
        if not isinstance(rec, dict):
            continue
        items.append(
            {
                "priority": rec.get("priority", "medium"),
                "title": rec.get("title", "Tax planning recommendation"),
                "message": rec.get("description", "Apply tax optimization recommendation."),
            }
        )

    issues_summary = (reconciliation_report.get("issues") or {}).get("summary", {})
    duplicate_count = int(issues_summary.get("duplicate_count", 0) or 0)
    low_confidence_count = int(issues_summary.get("low_confidence_count", 0) or 0)

    if duplicate_count > 0:
        items.append(
            {
                "priority": "high",
                "title": "Resolve Duplicate Transactions",
                "message": f"Found {duplicate_count} potential duplicates in reconciliation report.",
            }
        )

    if low_confidence_count > 0:
        items.append(
            {
                "priority": "medium",
                "title": "Review Low Confidence Entries",
                "message": f"Found {low_confidence_count} low-confidence classified entries.",
            }
        )

    if not items:
        items.append(
            {
                "priority": "low",
                "title": "No Critical Actions",
                "message": "No immediate actions identified. Continue periodic reconciliation and compliance checks.",
            }
        )

    return items[:12]


def _build_overall_report_doc(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    txns = fetch_user_transactions(user_id)

    profit_summary = get_profit_summary(txns)
    bookkeeping_summary = get_bookkeeping_summary(txns)
    expense_summary = get_expense_summary(txns)

    expected_balance = payload.get("expected_balance")
    expected_balance = _safe_float(expected_balance) if expected_balance is not None else None
    reconciliation_report = get_reconciliation_report(txns, expected_balance=expected_balance)
    tax_insights = get_tax_insights(txns)

    overall = profit_summary.get("overall", {})
    balance_summary = bookkeeping_summary.get("balance_summary", {})
    tax_summary = tax_insights.get("summary", {})

    total_revenue = _safe_float(overall.get("total_revenue"))
    total_expenses = _safe_float(overall.get("total_expenses"))
    net_profit = _safe_float(overall.get("net_profit"))
    total_itc = _safe_float(balance_summary.get("total_itc_claimable"))
    total_gst_paid = _safe_float(balance_summary.get("total_gst_paid"))

    report_id = payload.get("report_id") or f"overall-{uuid4().hex[:12]}"
    report_name = payload.get("report_name") or "Overall Financial Report"

    return {
        "report_id": report_id,
        "user_id": user_id,
        "report_name": report_name,
        "report_type": "overall_financial_report",
        "status": "generated",
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "profit_margin": _safe_float(overall.get("profit_margin_percent")),
            "net_cash_flow": _safe_float(balance_summary.get("net_cash_flow")),
            "claimable_itc": round(total_itc, 2),
            "gst_payable": round(max(total_gst_paid - total_itc, 0.0), 2),
            "taxable_income": round(max(net_profit, 0.0), 2),
            "potential_monthly_savings": _safe_float(tax_summary.get("potential_savings_per_month")),
            "potential_yearly_savings": _safe_float(tax_summary.get("potential_savings_per_year")),
        },
        "detailed_breakdown": {
            "profit": profit_summary,
            "bookkeeping": {
                "balance_summary": balance_summary,
                "entries_sample": bookkeeping_summary.get("entries", [])[:100],
            },
            "expenses": expense_summary,
            "reconciliation": reconciliation_report,
            "tax_planning": tax_insights,
        },
        "action_items": _build_action_items(bookkeeping_summary, tax_insights, reconciliation_report),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def generate_overall_report(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_doc = _build_overall_report_doc(user_id, payload or {})
    _overall_reports_collection().update_one(
        {"report_id": report_doc["report_id"]},
        {"$set": report_doc},
        upsert=True,
    )
    return report_doc


def get_overall_report(user_id: str, report_id: str) -> dict[str, Any]:
    report = _overall_reports_collection().find_one(
        {"user_id": user_id, "report_id": report_id},
        {"_id": 0},
    )
    if not report:
        return {"found": False, "report_id": report_id}
    return {"found": True, "report": report}


def _resolve_output_dir(raw_output_dir: str | None) -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    configured = raw_output_dir or config.OVERALL_REPORT_OUTPUT_DIR
    configured_path = Path(configured)
    if configured_path.is_absolute():
        output_dir = configured_path
    else:
        output_dir = backend_root / configured_path
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _render_overall_report_pdf(report_doc: dict[str, Any], output_dir: Path) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    report_id = report_doc.get("report_id", f"overall-{uuid4().hex[:8]}")
    filename = f"overall_report_{report_id}.pdf"
    full_path = output_dir / filename

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(full_path), pagesize=A4)
    story = []

    summary = report_doc.get("summary", {}) if isinstance(report_doc.get("summary"), dict) else {}

    story.append(Paragraph("Overall Financial Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Report ID: {report_id}", styles["Normal"]))
    story.append(Paragraph(f"User ID: {report_doc.get('user_id', '-')}", styles["Normal"]))
    story.append(Paragraph(f"Generated At: {report_doc.get('updated_at', _now_iso())}", styles["Normal"]))
    story.append(Spacer(1, 18))

    table_data = [
        ["Metric", "Value"],
        ["Total Revenue", _fmt_inr(summary.get("total_revenue"))],
        ["Total Expenses", _fmt_inr(summary.get("total_expenses"))],
        ["Net Profit", _fmt_inr(summary.get("net_profit"))],
        ["Net Cash Flow", _fmt_inr(summary.get("net_cash_flow"))],
        ["Claimable ITC", _fmt_inr(summary.get("claimable_itc"))],
        ["GST Payable", _fmt_inr(summary.get("gst_payable"))],
        ["Taxable Income", _fmt_inr(summary.get("taxable_income"))],
        ["Potential Monthly Savings", _fmt_inr(summary.get("potential_monthly_savings"))],
    ]

    table = Table(table_data, colWidths=[250, 220])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3A59")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F7FA")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Top Action Items", styles["Heading2"]))
    for item in (report_doc.get("action_items") or [])[:8]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Action")
        priority = str(item.get("priority") or "medium").upper()
        message = str(item.get("message") or "")
        story.append(Paragraph(f"[{priority}] <b>{title}</b>", styles["Normal"]))
        if message:
            story.append(Paragraph(message, styles["Normal"]))
        story.append(Spacer(1, 8))

    doc.build(story)
    return str(full_path)


def generate_overall_report_pdf(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    payload = payload or {}
    report_id = payload.get("report_id")

    if report_id:
        existing = _overall_reports_collection().find_one(
            {"user_id": user_id, "report_id": report_id},
            {"_id": 0},
        )
        if not existing:
            raise ValueError("Overall report not found for provided report_id")
        report_doc = existing
    else:
        report_doc = generate_overall_report(user_id, payload)
        report_id = report_doc["report_id"]

    output_dir = _resolve_output_dir(payload.get("output_dir"))
    pdf_path = _render_overall_report_pdf(report_doc, output_dir)

    _overall_reports_collection().update_one(
        {"user_id": user_id, "report_id": report_id},
        {"$set": {"pdf_path": pdf_path, "pdf_generated_at": _now_iso(), "updated_at": _now_iso()}},
        upsert=False,
    )

    return {
        "report_id": report_id,
        "pdf_path": pdf_path,
        "status": "pdf_generated",
    }


def _build_email_body(report_doc: dict[str, Any]) -> str:
    summary = report_doc.get("summary", {}) if isinstance(report_doc.get("summary"), dict) else {}
    return (
        "Hello,\n\n"
        "Please find your Overall Financial Report summary below:\n"
        f"- Report ID: {report_doc.get('report_id', '-')}\n"
        f"- Total Revenue: {_fmt_inr(summary.get('total_revenue'))}\n"
        f"- Total Expenses: {_fmt_inr(summary.get('total_expenses'))}\n"
        f"- Net Profit: {_fmt_inr(summary.get('net_profit'))}\n"
        f"- Net Cash Flow: {_fmt_inr(summary.get('net_cash_flow'))}\n"
        f"- Potential Monthly Savings: {_fmt_inr(summary.get('potential_monthly_savings'))}\n\n"
        "Regards,\nFinPilot"
    )


def email_overall_report(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_id = payload.get("report_id")
    if not report_id:
        raise ValueError("report_id is required")

    report_doc = _overall_reports_collection().find_one(
        {"user_id": user_id, "report_id": report_id},
        {"_id": 0},
    )
    if not report_doc:
        raise ValueError("Overall report not found")

    recipient = str(payload.get("email") or "").strip() or resolve_user_email(user_id)
    if not recipient:
        return {
            "sent": False,
            "report_id": report_id,
            "error": "No recipient email found. Provide email in request or update profile email.",
        }

    attach_pdf = bool(payload.get("attach_pdf", True))
    attachments: list[tuple[str, bytes, str]] = []

    if attach_pdf:
        pdf_path = str(report_doc.get("pdf_path") or "").strip()
        if not pdf_path or not Path(pdf_path).exists():
            pdf_result = generate_overall_report_pdf(
                user_id,
                {"report_id": report_id, "output_dir": payload.get("output_dir")},
            )
            pdf_path = pdf_result["pdf_path"]

        with open(pdf_path, "rb") as f:
            attachments.append((Path(pdf_path).name, f.read(), "application/pdf"))

    email_result = send_email(
        recipient=recipient,
        subject=f"Overall Financial Report - {report_id}",
        body=_build_email_body(report_doc),
        attachments=attachments,
    )

    _overall_reports_collection().update_one(
        {"user_id": user_id, "report_id": report_id},
        {
            "$set": {
                "last_emailed_at": _now_iso(),
                "last_email_status": email_result,
                "updated_at": _now_iso(),
            }
        },
        upsert=False,
    )

    return {
        "report_id": report_id,
        "recipient": recipient,
        "pdf_attached": bool(attachments),
        **email_result,
    }
