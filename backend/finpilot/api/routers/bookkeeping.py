from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from finpilot import config
from finpilot.api.deps import fetch_user_transactions
from finpilot.db.mongo import _get_db
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


def _safe_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _trend_pct(current: float, previous: float) -> float:
    if abs(previous) < 1e-9:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / abs(previous)) * 100.0


def _build_ai_insights(
    *,
    user_id: str,
    total_revenue: float,
    total_expenses: float,
    net_profit: float,
    tax_liability: float,
    uncategorized_count: int,
    recent_transactions: list[dict],
) -> list[dict]:
    min_insights = 6
    max_insights = 7

    if config.OPENAI_API_KEY and recent_transactions:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a CA-style financial analyst for Indian SMEs. "
                            "Return strict JSON with key insights containing 6 to 7 short, actionable insights."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"User: {user_id}\n"
                            f"Revenue: {total_revenue:.2f}\n"
                            f"Expenses: {total_expenses:.2f}\n"
                            f"Net Profit: {net_profit:.2f}\n"
                            f"Estimated Tax Liability: {tax_liability:.2f}\n"
                            f"Uncategorized Transactions: {uncategorized_count}\n"
                            f"Recent Transactions: {json.dumps(recent_transactions, default=str)}\n\n"
                            "Respond JSON as: {\"insights\":[\"...\"]}. "
                            "Provide 6 to 7 items."
                        ),
                    },
                ],
            )
            payload = json.loads(response.choices[0].message.content or "{}")
            insights = payload.get("insights")
            if isinstance(insights, list) and insights:
                cleaned = [str(item).strip() for item in insights if str(item).strip()][:max_insights]
                if cleaned:
                    if len(cleaned) < min_insights:
                        cleaned.extend(
                            [
                                "Review top 10 expense lines this week and flag non-essential outflows.",
                                "Set weekly reconciliation checkpoints to reduce month-end closing effort.",
                                "Track GST-ready invoices daily to avoid filing delays and credit mismatch.",
                            ][: min_insights - len(cleaned)]
                        )
                    return [{"type": "ai", "text": text} for text in cleaned[:max_insights]]
        except Exception:
            pass

    fallback: list[dict] = []
    if total_expenses > total_revenue and total_revenue > 0:
        fallback.append({
            "type": "risk",
            "text": "Expenses are higher than revenue in the current period. Review discretionary spend and vendor contracts.",
        })
    else:
        fallback.append({
            "type": "performance",
            "text": "Revenue is currently ahead of expenses. Maintain cash discipline and set aside tax reserves weekly.",
        })

    fallback.append({
        "type": "tax",
        "text": f"Estimated tax liability is ₹{tax_liability:,.0f}. Plan monthly set-asides to avoid quarter-end stress.",
    })

    fallback.append({
        "type": "cashflow",
        "text": f"Current net profit is ₹{net_profit:,.0f}. Build a 13-week cash-flow buffer and monitor it weekly.",
    })

    fallback.append({
        "type": "process",
        "text": "Reconcile bank and ledger entries at least once a week to reduce filing and audit friction.",
    })

    if uncategorized_count > 0:
        fallback.append({
            "type": "cleanup",
            "text": f"{uncategorized_count} transaction(s) are uncategorized. Classify them to improve report quality.",
        })
    else:
        fallback.append({
            "type": "quality",
            "text": "Transaction categorization quality looks good. Continue regular reconciliation for cleaner filings.",
        })

    fallback.append({
        "type": "compliance",
        "text": "Maintain a monthly compliance checklist for GST, TDS, and return deadlines to avoid penalties.",
    })

    if recent_transactions:
        latest = recent_transactions[0]
        fallback.append({
            "type": "recent",
            "text": f"Latest transaction trend check: review '{latest.get('desc', 'recent entry')}' to validate tagging and business relevance.",
        })

    fallback.append({
        "type": "planning",
        "text": "Create a monthly budget vs actual report and cap variance alerts at 10% for key categories.",
    })

    return fallback[:max_insights]


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


@router.get("/dashboard/{user_id}")
def dashboard_overview_route(user_id: str):
    try:
        txns = fetch_user_transactions(user_id)
        now = datetime.now()
        current_start = now - timedelta(days=30)
        previous_start = now - timedelta(days=60)

        total_revenue = sum(t.amount for t in txns if t.type == "credit")
        total_expenses = sum(t.amount for t in txns if t.type == "debit")
        net_profit = total_revenue - total_expenses
        tax_liability = sum(_safe_float(t.gst_amount) for t in txns if t.type == "credit")

        current_revenue = sum(t.amount for t in txns if t.type == "credit" and t.date >= current_start)
        previous_revenue = sum(
            t.amount for t in txns if t.type == "credit" and previous_start <= t.date < current_start
        )
        current_expenses = sum(t.amount for t in txns if t.type == "debit" and t.date >= current_start)
        previous_expenses = sum(
            t.amount for t in txns if t.type == "debit" and previous_start <= t.date < current_start
        )
        current_profit = current_revenue - current_expenses
        previous_profit = previous_revenue - previous_expenses

        uncategorized_count = sum(
            1 for t in txns if str(t.category or "").strip().lower() in {"", "uncategorized"}
        )

        recent = sorted(txns, key=lambda t: t.date, reverse=True)[:5]
        recent_transactions = [
            {
                "date": t.date.isoformat(),
                "desc": t.party,
                "amount": t.amount,
                "type": t.type,
                "status": "completed" if _safe_float(t.confidence) >= 0.7 else "review",
                "category": t.category,
            }
            for t in recent
        ]

        monthly_rollup: dict[str, dict[str, float]] = {}
        for t in txns:
            month_key = t.date.strftime("%Y-%m")
            if month_key not in monthly_rollup:
                monthly_rollup[month_key] = {"revenue": 0.0, "expenses": 0.0}
            if t.type == "credit":
                monthly_rollup[month_key]["revenue"] += _safe_float(t.amount)
            else:
                monthly_rollup[month_key]["expenses"] += _safe_float(t.amount)

        monthly_clusters: list[dict] = []
        year = now.year
        month = now.month
        for _ in range(6):
            key = f"{year:04d}-{month:02d}"
            bucket = monthly_rollup.get(key, {"revenue": 0.0, "expenses": 0.0})
            revenue = _safe_float(bucket.get("revenue"))
            expenses = _safe_float(bucket.get("expenses"))
            monthly_clusters.append(
                {
                    "month": datetime(year, month, 1).strftime("%b %y"),
                    "revenue": revenue,
                    "expenses": expenses,
                    "profit": revenue - expenses,
                }
            )

            month -= 1
            if month == 0:
                month = 12
                year -= 1

        monthly_clusters.reverse()

        profile_doc = _get_db()["profiles"].find_one({"user_id": user_id}, {"_id": 0}) or {}
        personal = profile_doc.get("personal_info") if isinstance(profile_doc.get("personal_info"), dict) else {}
        business = profile_doc.get("business_info") if isinstance(profile_doc.get("business_info"), dict) else {}

        pending_actions: list[dict] = []
        if not personal.get("full_name") or not personal.get("phone") or not business.get("business_name"):
            pending_actions.append({"title": "Complete profile details", "priority": "high"})
        if not txns:
            pending_actions.append({"title": "Upload a bank statement", "priority": "critical"})
        if uncategorized_count > 0:
            pending_actions.append({"title": "Review uncategorized transactions", "priority": "medium"})

        overdue_deadlines = _get_db()["deadlines"].count_documents(
            {"user_id": user_id, "status": {"$ne": "done"}, "due_date": {"$lt": now.isoformat()}}
        )
        if overdue_deadlines > 0:
            pending_actions.append({"title": f"Resolve {overdue_deadlines} overdue deadline(s)", "priority": "critical"})

        if not pending_actions:
            pending_actions = [{"title": "No urgent actions pending", "priority": "low"}]

        ai_insights = _build_ai_insights(
            user_id=user_id,
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            net_profit=net_profit,
            tax_liability=tax_liability,
            uncategorized_count=uncategorized_count,
            recent_transactions=recent_transactions,
        )

        return {
            "success": True,
            "data": {
                "kpis": {
                    "total_revenue": total_revenue,
                    "total_expenses": total_expenses,
                    "net_profit": net_profit,
                    "tax_liability": tax_liability,
                    "revenue_trend_pct": _trend_pct(current_revenue, previous_revenue),
                    "expenses_trend_pct": _trend_pct(current_expenses, previous_expenses),
                    "profit_trend_pct": _trend_pct(current_profit, previous_profit),
                    "tax_trend_pct": _trend_pct(sum(_safe_float(t.gst_amount) for t in txns if t.type == "credit" and t.date >= current_start), sum(_safe_float(t.gst_amount) for t in txns if t.type == "credit" and previous_start <= t.date < current_start)),
                },
                "recent_transactions": recent_transactions,
                "monthly_clusters": monthly_clusters,
                "pending_actions": pending_actions[:5],
                "ai_insights": ai_insights,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update-entry/{entry_id}")
def update_entry_route(entry_id: str, payload: BookkeepingUpdateEntryRequest):
    try:
        data = bookkeeping_update_entry(payload.user_id, entry_id, payload.updates)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
