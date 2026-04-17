"""
FastAPI Server Engine mapping AI extraction constraints and logic workflows 
dynamically into distinct operational HTTP intelligence endpoints securely.
"""
import os
import sys
import json
from datetime import datetime, timedelta
# Automatically bind the project root to the Python path avoiding module import errors
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Imports from pocket_cfo_parser core logic
from pocket_cfo_parser.ingestion import ingest_sms, ingest_pdf
from pocket_cfo_parser.db.mongo import get_transactions_by_user, save_user, save_transaction, compliance_calendar_collection
from pocket_cfo_parser.models.transaction import Transaction
from pocket_cfo_parser.agents.expense_agent import get_expense_summary
from pocket_cfo_parser.agents.profit_agent_v2 import get_profit_summary as get_profit_summary_v2
from pocket_cfo_parser.agents.gst_agent import analyze_itc_opportunities
from pocket_cfo_parser.agents.tax_savings_agent import get_tax_insights
from pocket_cfo_parser.agents.gstr_report_agent import generate_gst_compliance_report
from pocket_cfo_parser.agents.bookkeeping_agent import get_bookkeeping_summary
from pocket_cfo_parser.agents.financial_statements_agent import get_financial_statements
from pocket_cfo_parser.agents.income_tax_agent import get_income_tax_summary
from pocket_cfo_parser.agents.reconciliation_agent import get_reconciliation_report
from pocket_cfo_parser.agents.audit_agent import get_audit_report
from pocket_cfo_parser.compliance_engine import (
    W8BENData,
    create_aa_consent,
    create_payable_invoice,
    detect_oidar_rcm,
    fetch_aa_financial_data,
    generate_w8ben_pdf,
    mark_aa_data_ready,
    run_43bh_aging,
    run_gst_preflight,
    save_foreign_remittance,
    schedule_compliance_calendar,
    trigger_drl_if_missing_invoice,
    update_aa_consent_status,
    verify_msme_vendor,
    generate_ca_report_pdf,
    trigger_deadline_notifications,
    get_compliance_calendar_events
)

# Instantiate API architecture
app = FastAPI(
    title="Pocket CFO Agent API", 
    version="1.0.0"
)

# Safely inject permissive structural development bounds evaluating origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Expand origin scope globally (Will tightly bind down constraints explicitly later)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Construct specific strict payload representations natively mapping validations explicitly
class SMSPayload(BaseModel):
    user_id: str
    text: str

class UserCreatePayload(BaseModel):
    name: str
    phone: str
    business_name: str


class AAConsentPayload(BaseModel):
    user_id: str
    aa_handle: str
    fi_types: list[str]
    from_date: str
    to_date: str


class AAConsentWebhookPayload(BaseModel):
    consent_id: str
    status: str
    payload: dict | None = None


class AADataReadyPayload(BaseModel):
    consent_id: str
    session_id: str
    user_id: str
    payload: dict | None = None


class VendorVerifyPayload(BaseModel):
    user_id: str
    vendor_name: str
    pan: str
    udyam_number: str | None = None


class PayableCreatePayload(BaseModel):
    user_id: str
    vendor_pan: str
    invoice_number: str
    invoice_date: str
    amount: float


class W8BENPayload(BaseModel):
    full_name: str
    registered_address: str
    pan: str


class ForeignRemittancePayload(BaseModel):
    user_id: str
    remitter_name: str
    remitter_pan: str
    remittee_name: str
    remittee_country: str
    amount_inr: float
    purpose_code: str = "P0802"
    dtaa_applicable: bool = True
    taxability: str = "TAXABLE"
    withholding_rate: float = 0.0


class OidarCheckPayload(BaseModel):
    party: str
    amount: float


class GSTPreflightPayload(BaseModel):
    user_id: str
    gstr1_total_tax: float
    gstr3b_total_tax: float


class ComplianceCalendarPayload(BaseModel):
    user_id: str
    entity_type: str
    financial_year_end: str


class DRLPayload(BaseModel):
    user_id: str
    threshold_amount: float = 20000.0


class ReportAnalyzerPayload(BaseModel):
    user_id: str

@app.post("/users/create")
def create_user_route(payload: UserCreatePayload):
    """Dynamically structurally bounds OOP mappings routing native MongoDB user creation."""
    user_id = save_user(payload.name, payload.phone, payload.business_name)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return {"success": True, "backend_user_id": user_id}

@app.get("/users/{user_id}/profile")
def user_profile_route(user_id: str):
    """Evaluate topological boundaries aggregating transactional mapping counts securely natively."""
    txns = get_transactions_by_user(user_id)
    return {"user_id": user_id, "transaction_count": len(txns)}

@app.get("/transactions/{user_id}")
def user_transactions_route(user_id: str):
    """Exposes raw sequential MongoDB extractions cleanly bounded intrinsically iteratively."""
    txns = _fetch_user_transactions(user_id)
    sorted_txns = sorted(txns, key=lambda x: x.date, reverse=True)[:100]
    return {"transactions": [t.to_dict() for t in sorted_txns], "user_id": user_id}


@app.get("/health")
def health_check():
    """Simple healthcheck evaluating operational runtime uptime."""
    return {"status": "ok", "message": "Pocket CFO Agent is running"}


@app.post("/ingest/sms")
def ingest_sms_route(payload: SMSPayload):
    """
    Ingests fundamentally unstructured SMS structurally aggregating transaction flows 
    natively securely into databases implicitly resolving AI schemas.
    """
    txn = ingest_sms(payload.text, payload.user_id)
    if txn:
        return txn.to_dict()
    else:
        return {"status": "skipped", "reason": "non-transactional message"}


@app.post("/ingest/pdf")
async def ingest_pdf_route(user_id: str = Form(...), file: UploadFile = File(...)):
    """
    Uploads dynamic PDF structurally unpacking data matrices inherently 
    saving evaluated tables chronologically into DB reliably securely.
    """
    # Spawns isolated secure temporary container safely extracting native logic dimensions efficiently
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name
        
    try:
        transactions = ingest_pdf(tmp_path, user_id)
        return {
            "transactions": [t.to_dict() for t in transactions],
            "count": len(transactions)
        }
    finally:
        # Dynamically guarantee native file deletion safely resolving logic bottlenecks reliably mathematically
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _fetch_user_transactions(user_id: str) -> list[Transaction]:
    """
    Helper dynamically unpacking primitive Mongo database representations 
    safely compiling robust active OOP models explicitly properly structurally.
    """
    raw_dicts = get_transactions_by_user(user_id)
    txns = []
    
    for r in raw_dicts:
        raw_date = r.get("date")
        if isinstance(raw_date, str):
            try:
                txn_date = datetime.fromisoformat(raw_date)
            except ValueError:
                txn_date = datetime.now()
        elif isinstance(raw_date, datetime):
            txn_date = raw_date
        else:
            txn_date = datetime.now()

        txn = Transaction(
            amount=r.get("amount", 0.0),
            type=r.get("type", "debit"),
            party=r.get("party", "Unknown"),
            date=txn_date,
            source=r.get("source", "sms"),
            category=r.get("category", "Uncategorized"),
            sub_category=r.get("sub_category", "Uncategorized"),
            business_nature=r.get("business_nature", "business"),
            gst_rate=r.get("gst_rate", 0.0),
            itc_eligible=r.get("itc_eligible", False),
            hsn_sac=r.get("hsn_sac", "UNKNOWN"),
            gst_amount=r.get("gst_amount", 0.0),
            itc_amount=r.get("itc_amount", 0.0),
            matched_rule=r.get("matched_rule", "none"),
            raw_text=r.get("raw_text", ""),
            confidence=r.get("confidence", 0.9)
        )
        txns.append(txn)
        
    return txns


@app.get("/insights/{user_id}")
def insights_route(user_id: str):
    """
    High-level financial insights for dashboard.
    Quick overview of profit, expenses, and tax opportunities.
    """
    txns = _fetch_user_transactions(user_id)
    
    profit_data = get_profit_summary_v2(txns)
    expense_data = get_expense_summary(txns)
    tax_data = get_tax_insights(txns)
    
    expense_by_category = expense_data.get("categories", {})
    top_expense_categories = {
        cat: values.get("total_spent", 0.0)
        for cat, values in sorted(
            expense_by_category.items(),
            key=lambda item: item[1].get("total_spent", 0.0),
            reverse=True
        )[:5]
    }
    # Keep both old and new keys so frontend pages remain stable.
    profit_overall = profit_data.get("overall", {})
    profit_compat = {
        "total_revenue": profit_overall.get("total_revenue", 0.0),
        "total_expenses": profit_overall.get("total_expenses", 0.0),
        "net_profit": profit_overall.get("net_profit", 0.0),
        "profit_margin": profit_overall.get("profit_margin_percent", 0.0),
        "summary": profit_overall.get("verdict", "No profit summary available."),
        "revenue_transactions": profit_overall.get("revenue_transactions", 0),
        "expense_transactions": profit_overall.get("expense_transactions", 0),
        "total_gst_paid": profit_overall.get("total_gst_paid", 0.0),
        "total_itc_claimable": profit_overall.get("total_itc_claimable", 0.0),
        "effective_tax_rate": (
            round(
                (profit_overall.get("total_gst_paid", 0.0) / profit_overall.get("total_expenses", 1.0)) * 100,
                2
            ) if profit_overall.get("total_expenses", 0.0) > 0 else 0.0
        ),
        "itc_tip": (
            f"Potential ITC recovery is ₹{profit_overall.get('total_itc_claimable', 0.0):,.2f}."
            if profit_overall.get("total_itc_claimable", 0.0) > 0
            else "No major ITC recovery opportunity found for current data."
        )
    }
    expense_compat = {
        "total_expenses": expense_data.get("total_expenses", 0.0),
        "by_category": {
            cat: values.get("total_spent", 0.0)
            for cat, values in expense_by_category.items()
        },
        "top_category": expense_data.get("top_category"),
        "anomalies": expense_data.get("anomalies", []),
        "anomaly_count": expense_data.get("anomaly_count", 0),
        "insight": expense_data.get("insight", "")
    }

    return {
        "user_id": user_id,
        "financial_overview": {
            "period": "Last 30 days",
            "net_profit": profit_overall.get("net_profit", 0.0),
            "total_revenue": profit_overall.get("total_revenue", 0.0),
            "total_expenses": profit_overall.get("total_expenses", 0.0),
            "profit_margin_percent": profit_overall.get("profit_margin_percent", 0.0),
            "transactions_processed": profit_overall.get("transaction_count", 0)
        },
        "top_expense_categories": top_expense_categories,
        "tax_opportunities": {
            "potential_monthly_savings": tax_data["summary"]["potential_savings_per_month"],
            "quick_wins": tax_data["quick_wins"],
            "total_action_items": tax_data["summary"]["total_action_items"]
        },
        "expense_summary": expense_compat,
        "profit_summary": profit_compat,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/expenses/{user_id}")
def expenses_route(user_id: str):
    txns = _fetch_user_transactions(user_id)
    return get_expense_summary(txns)


@app.get("/profit/{user_id}")
def profit_route(user_id: str):
    txns = _fetch_user_transactions(user_id)
    return get_profit_summary_v2(txns)


@app.get("/tax-savings/{user_id}")
def tax_savings_route(user_id: str):
    """
    Tax optimization strategies and potential savings.
    Recommends ways to maximize ITC, optimize expenses, and reduce tax burden.
    """
    txns = _fetch_user_transactions(user_id)
    insights = get_tax_insights(txns)
    return {
        "user_id": user_id,
        "tax_insights": insights,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/bookkeeping/{user_id}")
def bookkeeping_route(user_id: str):
    """
    Bookkeeping summary for ledger review.
    Includes cashbook entries, category counts, GST and ITC totals, and bookkeeping remarks.
    """
    txns = _fetch_user_transactions(user_id)
    summary = get_bookkeeping_summary(txns)
    return {
        "user_id": user_id,
        "bookkeeping_summary": summary,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/gst-report/{user_id}")
def gst_report_route(user_id: str):
    """
    Complete GST compliance report package:
    - GSTR-1 draft (outward supplies)
    - GSTR-3B draft (monthly return)
    - ITC summary
    - Filing checklist
    """
    txns = _fetch_user_transactions(user_id)
    report = generate_gst_compliance_report(txns)
    return {
        "user_id": user_id,
        "report": report
    }


@app.get("/financial-statements/{user_id}")
def financial_statements_route(user_id: str):
    """
    Generate core financial statements for CA review:
    - Profit & Loss statement
    - Simplified Balance Sheet
    - Cash Flow statement
    """
    txns = _fetch_user_transactions(user_id)
    statements = get_financial_statements(txns)
    return {
        "user_id": user_id,
        "financial_statements": statements,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/income-tax/{user_id}")
def income_tax_route(user_id: str):
    """
    Estimate income tax liability and common deductions based on transaction history.
    """
    txns = _fetch_user_transactions(user_id)
    summary = get_income_tax_summary(txns)
    return {
        "user_id": user_id,
        "income_tax_summary": summary,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/reconciliation/{user_id}")
def reconciliation_route(user_id: str):
    """
    Run a reconciliation assessment to detect duplicates, gaps, and matching issues.
    """
    txns = _fetch_user_transactions(user_id)
    report = get_reconciliation_report(txns)
    return {
        "user_id": user_id,
        "reconciliation_report": report,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/audit/{user_id}")
def audit_route(user_id: str):
    """
    Audit and validate transaction accuracy, GST consistency, and suspicious patterns.
    """
    txns = _fetch_user_transactions(user_id)
    report = get_audit_report(txns)
    return {
        "user_id": user_id,
        "audit_report": report,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/ca-summary/{user_id}")
def ca_summary_route(user_id: str):
    """
    Complete CA-level financial summary for the user.
    Combines: Profit, Expenses, Tax Savings, and GST Compliance.
    """
    txns = _fetch_user_transactions(user_id)
    
    profit_data = get_profit_summary_v2(txns)
    expense_data = get_expense_summary(txns)
    tax_data = get_tax_insights(txns)
    gst_data = generate_gst_compliance_report(txns)
    financial_statements = get_financial_statements(txns)
    income_tax = get_income_tax_summary(txns)
    reconciliation = get_reconciliation_report(txns)
    audit = get_audit_report(txns)
    
    action_items = []
    for item in tax_data.get("full_plan", {}).get("expense_gaps", []):
        action_items.append({
            "priority": item.get("priority", "info"),
            "title": item.get("title", "Tax opportunity"),
            "message": item.get("description") or item.get("action", "")
        })
    for item in tax_data.get("full_plan", {}).get("optimization_tips", []):
        action_items.append({
            "priority": item.get("priority", "info"),
            "title": item.get("title", "Optimization tip"),
            "message": item.get("description") or item.get("action", "")
        })
    for item in tax_data.get("full_plan", {}).get("missed_itc_opportunities", [])[:5]:
        action_items.append({
            "priority": "medium",
            "title": f"Review ITC for {item.get('party', 'transaction')}",
            "message": item.get("recommendation", "")
        })

    return {
        "user_id": user_id,
        "summary": {
            "net_profit": profit_data["overall"]["net_profit"],
            "total_revenue": profit_data["overall"]["total_revenue"],
            "total_expenses": profit_data["overall"]["total_expenses"],
            "profit_margin": profit_data["overall"]["profit_margin_percent"],
            "potential_monthly_savings": tax_data["summary"]["potential_savings_per_month"],
            "claimable_itc": tax_data["summary"]["potential_savings_per_month"],
            "gst_payable": gst_data["gstr_3b"]["section_3_net_payable"]["net_gst_payable"],
            "refund_available": gst_data["gstr_3b"]["section_3_net_payable"]["net_refund_available"],
            "taxable_income": income_tax["taxable_income_summary"]["taxable_income"],
            "reconciliation_issues": reconciliation["issues"]["summary"],
            "audit_flags": audit["summary"]
        },
        "detailed_breakdown": {
            "profit": profit_data,
            "expenses": expense_data,
            "tax_opportunities": tax_data,
            "gst_compliance": {"report": gst_data},
            "financial_statements": financial_statements,
            "income_tax": income_tax,
            "reconciliation": reconciliation,
            "audit": audit
        },
        "action_items": action_items,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/ca-summary/{user_id}/pdf")
def ca_summary_pdf_route(user_id: str):
  
    # Generate the full JSON report internally
    report_data = ca_summary_route(user_id)
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated")
    
    # Pass to the reportlab generator
    pdf_path = generate_ca_report_pdf(user_id, report_data, out_dir)
    
    return FileResponse(
        pdf_path, 
        media_type="application/pdf", 
        filename=os.path.basename(pdf_path)
    )


@app.get("/gst/{user_id}")
def gst_route(user_id: str):
    txns = _fetch_user_transactions(user_id)
    return analyze_itc_opportunities(txns)


@app.get("/actions/{user_id}")
def actions_route(user_id: str):
    """
    Dynamically groups systemic diagnostic evaluations mapping triggers directly 
    translating numerical bounds trajectories into actionable operational dashboard components.
    """
    txns = _fetch_user_transactions(user_id)
    actions = []
    
    expenses = get_expense_summary(txns)
    profits = get_profit_summary_v2(txns)
    itc_ops = analyze_itc_opportunities(txns)
    
    # 1. Red Cards (Critical Focus Required): Expense anomalies, Overall negative balances implicitly 
    for anomaly in expenses.get("anomalies", []):
        amt = anomaly.get("transaction", {}).get("amount", None)
        actions.append({
            "priority": "red",
            "title": "Unusual Spending Outlier Detected",
            "message": anomaly.get("anomaly_reason", "High mathematical variance explicitly defined bounds."),
            "amount": amt
        })
        
    net_profit = profits.get("overall", {}).get("net_profit", 0.0)
    if net_profit < 0:
        actions.append({
            "priority": "red",
            "title": "Deficit Bounds Alert",
            "message": "You're operating at a loss this period. Review your top expense categories to cut costs.",
            "amount": abs(net_profit)
        })
        
    # 2. Amber Cards (Warnings/Checks): Missed ITC structurally explicit bounds natively mapped
    missed_itc = itc_ops.get("missed_itc_count", 0)
    if missed_itc > 0:
        actions.append({
            "priority": "amber",
            "title": "Missed Input Tax Credit Diagnostics",
            "message": f"You have {missed_itc} transactions we couldn't classify confidently. Review them to unlock potential ITC claims.",
            "amount": None
        })
        
    low_confidence_count = sum(1 for t in txns if t.confidence <= 0.4)
    if low_confidence_count > 0:
        actions.append({
            "priority": "amber",
            "title": "Review Classification Thresholds natively",
            "message": f"AI couldn't classify {low_confidence_count} transactions with high confidence. Review and tag them manually.",
            "amount": None
        })
        
    # 3. Green Cards (Success/Goals): Profitable, High ITC dependencies structurally evaluated implicitly 
    claimable_itc = itc_ops.get("total_itc_claimable", 0.0)
    if claimable_itc > 0:
        actions.append({
            "priority": "green",
            "title": "Input Tax Credit Available",
            "message": f"You can claim ₹{claimable_itc:,.2f} in GST credits. File your ITC claims to improve cashflow.",
            "amount": claimable_itc
        })
        
    if net_profit > 0:
        actions.append({
            "priority": "green",
            "title": "Business is Profitable",
            "message": f"You made ₹{net_profit:,.2f} this period after expenses and GST recovery. Keep it up.",
            "amount": net_profit
        })

    return {
        "actions": actions,
        "user_id": user_id
    }


@app.post("/seed/demo/{user_id}")
def seed_demo_data_route(user_id: str, months: int = Query(default=6, ge=1, le=12)):
    """
    Seed deterministic demo transactions for hackathon testing.
    Useful for tax, audit, reconciliation, and trend views.
    """
    now = datetime.now()
    saved = 0
    txns: list[Transaction] = []

    for m in range(months):
        month_offset = (months - 1) - m
        base_date = now.replace(day=10) - timedelta(days=30 * month_offset)
        month_tag = base_date.strftime("%b-%Y")

        # Revenue credits
        txns.extend([
            Transaction(
                amount=85000 + (m * 2200),
                type="credit",
                party="Retail Sales",
                date=base_date.replace(day=3, hour=10, minute=0, second=0, microsecond=0),
                source="sms",
                raw_text=f"UPI credit from sales batch {month_tag}",
                category="Sales Income",
                sub_category="Retail",
                business_nature="business",
                confidence=0.96
            ),
            Transaction(
                amount=22000 + (m * 900),
                type="credit",
                party="Online Orders",
                date=base_date.replace(day=7, hour=15, minute=15, second=0, microsecond=0),
                source="sms",
                raw_text=f"UPI credit online settlement {month_tag}",
                category="Sales Income",
                sub_category="Online",
                business_nature="business",
                confidence=0.94
            ),
        ])

        # Operating debits with GST mix
        txns.extend([
            Transaction(
                amount=16000 + (m * 400),
                type="debit",
                party="Warehouse Rent",
                date=base_date.replace(day=5, hour=9, minute=0, second=0, microsecond=0),
                source="sms",
                raw_text=f"Rent payment {month_tag}",
                category="Rent & Real Estate",
                sub_category="Rent",
                business_nature="business",
                gst_rate=18.0,
                itc_eligible=True,
                hsn_sac="9972",
                gst_amount=round((16000 + (m * 400)) * 18 / 118, 2),
                itc_amount=round((16000 + (m * 400)) * 18 / 118, 2),
                matched_rule="rent",
                confidence=0.93
            ),
            Transaction(
                amount=12500 + (m * 350),
                type="debit",
                party="Porter Logistics",
                date=base_date.replace(day=12, hour=13, minute=0, second=0, microsecond=0),
                source="sms",
                raw_text=f"Logistics expense {month_tag}",
                category="Logistics",
                sub_category="Courier & Delivery",
                business_nature="business",
                gst_rate=18.0,
                itc_eligible=True,
                hsn_sac="9967",
                gst_amount=round((12500 + (m * 350)) * 18 / 118, 2),
                itc_amount=round((12500 + (m * 350)) * 18 / 118, 2),
                matched_rule="porter",
                confidence=0.91
            ),
            Transaction(
                amount=6800 + (m * 180),
                type="debit",
                party="Airtel Business",
                date=base_date.replace(day=15, hour=11, minute=30, second=0, microsecond=0),
                source="sms",
                raw_text=f"Telecom recharge {month_tag}",
                category="Telecommunications",
                sub_category="Internet",
                business_nature="business",
                gst_rate=18.0,
                itc_eligible=True,
                hsn_sac="9984",
                gst_amount=round((6800 + (m * 180)) * 18 / 118, 2),
                itc_amount=round((6800 + (m * 180)) * 18 / 118, 2),
                matched_rule="airtel",
                confidence=0.89
            ),
            Transaction(
                amount=5400 + (m * 120),
                type="debit",
                party="Swiggy",
                date=base_date.replace(day=18, hour=14, minute=0, second=0, microsecond=0),
                source="sms",
                raw_text=f"Food expense {month_tag}",
                category="Food & Beverage",
                sub_category="Team Meals",
                business_nature="business",
                gst_rate=5.0,
                itc_eligible=False,
                hsn_sac="9963",
                gst_amount=round((5400 + (m * 120)) * 5 / 105, 2),
                itc_amount=0.0,
                matched_rule="swiggy",
                confidence=0.87
            ),
            Transaction(
                amount=4200 + (m * 140),
                type="debit",
                party="Term Insurance Premium",
                date=base_date.replace(day=19, hour=10, minute=15, second=0, microsecond=0),
                source="sms",
                raw_text=f"Insurance premium {month_tag}",
                category="Financial Services",
                sub_category="Insurance",
                business_nature="personal",
                gst_rate=18.0,
                itc_eligible=False,
                hsn_sac="9971",
                gst_amount=round((4200 + (m * 140)) * 18 / 118, 2),
                itc_amount=0.0,
                matched_rule="insurance",
                confidence=0.9
            ),
            Transaction(
                amount=3600 + (m * 100),
                type="debit",
                party="Education Course Platform",
                date=base_date.replace(day=22, hour=12, minute=5, second=0, microsecond=0),
                source="sms",
                raw_text=f"Education spend {month_tag}",
                category="Education",
                sub_category="Skill Development",
                business_nature="personal",
                gst_rate=18.0,
                itc_eligible=False,
                hsn_sac="9992",
                gst_amount=round((3600 + (m * 100)) * 18 / 118, 2),
                itc_amount=0.0,
                matched_rule="education",
                confidence=0.88
            ),
            Transaction(
                amount=5000 + (m * 160),
                type="debit",
                party="Mutual Fund SIP",
                date=base_date.replace(day=24, hour=9, minute=30, second=0, microsecond=0),
                source="sms",
                raw_text=f"Investment SIP {month_tag}",
                category="Investments",
                sub_category="Mutual Funds",
                business_nature="personal",
                gst_rate=18.0,
                itc_eligible=False,
                hsn_sac="9971",
                gst_amount=round((5000 + (m * 160)) * 18 / 118, 2),
                itc_amount=0.0,
                matched_rule="mutual-fund",
                confidence=0.9
            ),
            Transaction(
                amount=7600 + (m * 250),
                type="debit",
                party="Fuel Station",
                date=base_date.replace(day=21, hour=18, minute=0, second=0, microsecond=0),
                source="sms",
                raw_text=f"Fuel bill {month_tag}",
                category="Fuel",
                sub_category="Transport Fuel",
                business_nature="business",
                gst_rate=0.0,
                itc_eligible=False,
                hsn_sac="EXEMPT",
                gst_amount=0.0,
                itc_amount=0.0,
                matched_rule="fuel",
                confidence=0.84
            ),
        ])

        # Low-confidence and anomaly-style debits for audit/reconciliation testing
        txns.append(
            Transaction(
                amount=41500 if m % 2 == 0 else 28900,
                type="debit",
                party="Unknown Vendor",
                date=base_date.replace(day=26, hour=16, minute=10, second=0, microsecond=0),
                source="sms",
                raw_text=f"Misc expense {month_tag}",
                category="General Business Expense",
                sub_category="General",
                business_nature="business",
                gst_rate=18.0,
                itc_eligible=False,
                hsn_sac="UNKNOWN",
                gst_amount=0.0,
                itc_amount=0.0,
                matched_rule="fallback",
                confidence=0.32
            )
        )

    for txn in txns:
        result = save_transaction(txn, user_id)
        if result is not None:
            saved += 1

    return {
        "user_id": user_id,
        "seeded_transactions": saved,
        "months_covered": months,
        "message": "Demo data seeded successfully. You can now test tax, audit, reconciliation, and income tax agents."
    }


@app.get("/what-if/{user_id}")
def what_if_route(
    user_id: str,
    expense_category: str = Query(default=""),
    reduction_percent: float = Query(default=10.0, ge=0.0, le=100.0),
    revenue_increase_percent: float = Query(default=0.0, ge=0.0, le=100.0)
):
    """
    Lightweight simulation for hackathon demos.
    Estimates net-profit impact if expense category spend is reduced and/or revenue grows.
    """
    txns = _fetch_user_transactions(user_id)
    if not txns:
        return {
            "user_id": user_id,
            "scenario": {
                "expense_category": expense_category or "All Categories",
                "reduction_percent": reduction_percent,
                "revenue_increase_percent": revenue_increase_percent
            },
            "message": "No transactions available for simulation.",
            "baseline": {},
            "simulation": {},
            "impact": {}
        }

    baseline = get_profit_summary_v2(txns).get("overall", {})
    expense_data = get_expense_summary(txns)
    categories = expense_data.get("categories", {})

    base_revenue = baseline.get("total_revenue", 0.0)
    base_expenses = baseline.get("total_business_expenses", baseline.get("total_expenses", 0.0))
    base_itc = baseline.get("total_itc_claimable", 0.0)
    base_net = baseline.get("net_profit", 0.0)

    selected_category = expense_category.strip()
    matched_category = None
    if selected_category:
        for cat in categories:
            if cat.lower() == selected_category.lower():
                matched_category = cat
                break

    reduction_base = 0.0
    if matched_category:
        reduction_base = categories.get(matched_category, {}).get("total_spent", 0.0)
    else:
        reduction_base = sum(values.get("total_spent", 0.0) for values in categories.values())
        matched_category = "All Categories"

    expense_reduction = round(reduction_base * (reduction_percent / 100), 2)
    revenue_increase = round(base_revenue * (revenue_increase_percent / 100), 2)

    simulated_revenue = round(base_revenue + revenue_increase, 2)
    simulated_expenses = round(max(base_expenses - expense_reduction, 0.0), 2)
    simulated_net = round(simulated_revenue - simulated_expenses + base_itc, 2)
    simulated_margin = round((simulated_net / simulated_revenue * 100), 2) if simulated_revenue > 0 else 0.0

    return {
        "user_id": user_id,
        "scenario": {
            "expense_category": matched_category,
            "reduction_percent": reduction_percent,
            "revenue_increase_percent": revenue_increase_percent
        },
        "baseline": {
            "revenue": round(base_revenue, 2),
            "expenses": round(base_expenses, 2),
            "itc_claimable": round(base_itc, 2),
            "net_profit": round(base_net, 2),
            "profit_margin_percent": round(baseline.get("profit_margin_percent", 0.0), 2)
        },
        "simulation": {
            "revenue": simulated_revenue,
            "expenses": simulated_expenses,
            "itc_claimable": round(base_itc, 2),
            "net_profit": simulated_net,
            "profit_margin_percent": simulated_margin
        },
        "impact": {
            "expense_reduction_amount": expense_reduction,
            "revenue_increase_amount": revenue_increase,
            "net_profit_delta": round(simulated_net - base_net, 2),
            "margin_delta": round(simulated_margin - baseline.get("profit_margin_percent", 0.0), 2)
        },
        "generated_at": datetime.now().isoformat()
    }


# -----------------------------
# Phase 1: AA integration routes
# -----------------------------
@app.post("/aa/consent/request")
def aa_consent_request_route(payload: AAConsentPayload):
    return create_aa_consent(
        user_id=payload.user_id,
        aa_handle=payload.aa_handle,
        fi_types=payload.fi_types,
        from_date=payload.from_date,
        to_date=payload.to_date,
    )


@app.post("/aa/webhook/consent")
def aa_consent_webhook_route(payload: AAConsentWebhookPayload):
    return update_aa_consent_status(payload.consent_id, payload.status, payload.payload)


@app.post("/aa/webhook/data-ready")
def aa_data_ready_webhook_route(payload: AADataReadyPayload):
    mark_aa_data_ready(payload.consent_id, payload.session_id, payload.payload)
    fetch_result = fetch_aa_financial_data(payload.consent_id, payload.session_id, payload.user_id)
    return {"status": "processed", "fetch_result": fetch_result}


# -----------------------------
# Phase 2: MSME + 43B(h)
# -----------------------------
@app.post("/vendors/verify-msme")
def verify_msme_route(payload: VendorVerifyPayload):
    return verify_msme_vendor(
        user_id=payload.user_id,
        vendor_name=payload.vendor_name,
        pan=payload.pan,
        udyam_number=payload.udyam_number,
    )


@app.post("/payables/create")
def create_payable_route(payload: PayableCreatePayload):
    return create_payable_invoice(
        user_id=payload.user_id,
        vendor_pan=payload.vendor_pan,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        amount=payload.amount,
    )


@app.get("/payables/43bh/{user_id}")
def run_43bh_route(user_id: str):
    return run_43bh_aging(user_id)


# -----------------------------
# Phase 3: W-8BEN + 15CA
# -----------------------------
@app.post("/compliance/w8ben/generate")
def generate_w8ben_route(payload: W8BENPayload):
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated")
    pdf_path = generate_w8ben_pdf(
        W8BENData(
            full_name=payload.full_name,
            registered_address=payload.registered_address,
            pan=payload.pan.upper(),
        ),
        output_dir=output_dir,
    )
    return {"status": "generated", "file_path": pdf_path}


@app.post("/compliance/foreign-remittance")
def create_foreign_remittance_route(payload: ForeignRemittancePayload):
    return save_foreign_remittance(
        user_id=payload.user_id,
        remittance=payload.model_dump(),
    )


# -----------------------------
# Phase 4: OIDAR + GST preflight
# -----------------------------
@app.post("/compliance/oidar/check")
def oidar_check_route(payload: OidarCheckPayload):
    return detect_oidar_rcm(payload.party, payload.amount)


@app.post("/compliance/gst/preflight")
def gst_preflight_route(payload: GSTPreflightPayload):
    return run_gst_preflight(
        gstr1_total_tax=payload.gstr1_total_tax,
        gstr3b_total_tax=payload.gstr3b_total_tax,
        user_id=payload.user_id,
    )


# -----------------------------
# Phase 5: Compliance calendar + DRL
# -----------------------------
@app.post("/compliance/calendar/schedule")
def schedule_calendar_route(payload: ComplianceCalendarPayload):
    return schedule_compliance_calendar(
        user_id=payload.user_id,
        entity_type=payload.entity_type,
        financial_year_end=payload.financial_year_end,
    )


@app.post("/compliance/drl/trigger")
def trigger_drl_route(payload: DRLPayload):
    return trigger_drl_if_missing_invoice(payload.user_id, payload.threshold_amount)


@app.post("/compliance/calendar/notify/{user_id}")
def notify_calendar_route(user_id: str):
    """
    Trigger automated WhatsApp/Email notifications with OpenAI insights 
    for upcoming deadlines.
    """
    return trigger_deadline_notifications(user_id)


@app.post("/compliance/calendar/auto/{user_id}")
def auto_schedule_calendar_from_transactions_route(user_id: str):
    """
    Auto-schedule compliance calendar from parsed transaction history.
    Uses latest transaction date to infer financial year-end (Mar 31) and
    defaults entity type to pvt_ltd for hackathon demo.
    """
    txns = _fetch_user_transactions(user_id)
    if txns:
        latest_txn_date = max(t.date for t in txns)
        fy_year = latest_txn_date.year if latest_txn_date.month <= 3 else latest_txn_date.year + 1
    else:
        now = datetime.now()
        fy_year = now.year if now.month <= 3 else now.year + 1

    fy_end = f"{fy_year}-03-31"
    result = schedule_compliance_calendar(
        user_id=user_id,
        entity_type="pvt_ltd",
        financial_year_end=fy_end,
    )
    return {
        "user_id": user_id,
        "derived_from_transactions": True,
        "entity_type": "pvt_ltd",
        "financial_year_end": fy_end,
        "calendar": result,
    }


@app.get("/compliance/calendar/{user_id}")
def get_compliance_calendar_route(user_id: str):
    """
    Get the scheduled compliance calendar for a user.
    Returns calendar document and upcoming reminders for UI display.
    """
    from pocket_cfo_parser.db.mongo import compliance_calendar_collection
    doc = compliance_calendar_collection.find_one({"user_id": user_id})
    if not doc:
        return {"user_id": user_id, "message": "No calendar scheduled. Use /compliance/calendar/auto/{user_id} to create one."}
    
    # Convert MongoDB document to JSON-serializable dict
    calendar = {
        "user_id": doc.get("user_id"),
        "entity_type": doc.get("entity_type"),
        "financial_year_end": doc.get("financial_year_end"),
        "reminders": doc.get("reminders", []),
        "created_at": doc.get("created_at"),
    }
    
    # Get upcoming reminders (next 30 days)
    today = datetime.now().date()
    upcoming = []
    for r in doc.get("reminders", []):
        reminder_date = datetime.fromisoformat(r["reminder_date"]).date()
        if reminder_date >= today and (reminder_date - today).days <= 30:
            upcoming.append(r)
    
    # Sort by reminder date
    upcoming.sort(key=lambda x: x["reminder_date"])
    
    return {
        "user_id": user_id,
        "calendar": calendar,
        "upcoming": upcoming[:10],  # Top 10 upcoming
        "total_reminders": len(doc.get("reminders", []))
    }


@app.get("/compliance/calendar/{user_id}/events")
def get_compliance_calendar_events_route(user_id: str):
    """
    Returns compliance deadlines formatted as calendar events for UI display.
    Useful for integrating with calendar widgets or scheduling apps.
    """
    return get_compliance_calendar_events(user_id)


@app.get("/reports/generate-all/{user_id}")
def generate_all_reports_route(user_id: str):
    """
    Generate all major reports in one API call.
    """
    txns = _fetch_user_transactions(user_id)
    if not txns:
        return {
            "user_id": user_id,
            "generated_at": datetime.now().isoformat(),
            "status": "no_data",
            "message": "No transactions found. Ingest SMS/PDF/AA data first.",
            "reports": {},
        }

    profit_data = get_profit_summary_v2(txns)
    expense_data = get_expense_summary(txns)
    tax_data = get_tax_insights(txns)
    gst_data = generate_gst_compliance_report(txns)
    bookkeeping = get_bookkeeping_summary(txns)
    financial_statements = get_financial_statements(txns)
    income_tax = get_income_tax_summary(txns)
    reconciliation = get_reconciliation_report(txns)
    audit = get_audit_report(txns)
    actions = actions_route(user_id)

    return {
        "user_id": user_id,
        "generated_at": datetime.now().isoformat(),
        "status": "ok",
        "reports": {
            "profit": profit_data,
            "expenses": expense_data,
            "tax_savings": tax_data,
            "gst_report": gst_data,
            "bookkeeping": bookkeeping,
            "financial_statements": financial_statements,
            "income_tax": income_tax,
            "reconciliation": reconciliation,
            "audit": audit,
            "actions": actions,
        },
    }


@app.get("/reports/download/{user_id}")
def download_reports_bundle_route(user_id: str, format: str = Query(default="json")):
    bundle = generate_all_reports_route(user_id)
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated")
    os.makedirs(out_dir, exist_ok=True)

    if format.lower() == "json":
        filename = f"reports_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(out_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
        return FileResponse(path, media_type="application/json", filename=filename)

    raise HTTPException(status_code=400, detail="Unsupported format. Use format=json")


@app.post("/reports/analyze")
def analyze_reports_route(payload: ReportAnalyzerPayload):
    """
    Analyze generated reports and produce an executive summary with risk score.
    """
    bundle = generate_all_reports_route(payload.user_id)
    if bundle.get("status") != "ok":
        return {
            "user_id": payload.user_id,
            "status": "no_data",
            "analysis": {
                "summary": "No report data available to analyze.",
                "risk_score": 0,
                "highlights": [],
                "recommendations": ["Ingest data and generate reports first."],
            },
        }

    reports = bundle["reports"]
    profit_overall = reports.get("profit", {}).get("overall", {})
    net_profit = float(profit_overall.get("net_profit", 0.0))
    margin = float(profit_overall.get("profit_margin_percent", 0.0))
    tax_liability = float(
        reports.get("income_tax", {})
        .get("tax_liability", {})
        .get("total_tax_liability", 0.0)
    )
    recon_summary = reports.get("reconciliation", {}).get("issues", {}).get("summary", {})
    audit_summary = reports.get("audit", {}).get("summary", {})
    action_cards = reports.get("actions", {}).get("actions", [])
    critical_actions = len([a for a in action_cards if a.get("priority") == "red"])

    # Simple risk scoring for demo
    risk_score = 20
    if net_profit < 0:
        risk_score += 30
    if margin < 10:
        risk_score += 15
    risk_score += min(20, int(recon_summary.get("low_confidence_count", 0)) * 2)
    risk_score += min(20, int(audit_summary.get("suspicious_transactions_count", 0)))
    risk_score += min(15, critical_actions * 5)
    risk_score = min(100, max(0, risk_score))

    highlights = [
        f"Net profit: ₹{net_profit:,.2f}",
        f"Profit margin: {margin:.2f}%",
        f"Estimated income tax liability: ₹{tax_liability:,.2f}",
        f"Reconciliation low-confidence items: {recon_summary.get('low_confidence_count', 0)}",
        f"Audit suspicious transactions: {audit_summary.get('suspicious_transactions_count', 0)}",
        f"Critical action cards: {critical_actions}",
    ]

    recommendations: list[str] = []
    if net_profit < 0:
        recommendations.append("Prioritize cost reduction and improve receivables to restore profitability.")
    if recon_summary.get("low_confidence_count", 0) > 0:
        recommendations.append("Review low-confidence transactions to improve filing accuracy.")
    if audit_summary.get("gst_issues_count", 0) > 0:
        recommendations.append("Resolve GST validation issues before filing to avoid notices.")
    if not recommendations:
        recommendations.append("Financial and compliance health looks stable. Maintain monthly monitoring.")

    # Optional OpenAI structured analysis augmentation (fallback if not configured)
    ai = {"executive_summary": "", "top_risks": [], "next_actions": []}
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            context = {
                "risk_score": risk_score,
                "highlights": highlights,
                "recommendations": recommendations,
                "profit": reports.get("profit", {}).get("overall", {}),
                "income_tax": reports.get("income_tax", {}).get("tax_liability", {}),
                "audit": reports.get("audit", {}).get("summary", {}),
                "reconciliation": reports.get("reconciliation", {}).get("issues", {}).get("summary", {}),
                "actions": reports.get("actions", {}).get("actions", [])[:8],
            }
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a CFO-style compliance report analyst for Indian MSMEs. Return JSON only. No fluff."},
                    {"role": "user", "content": "Given this report context, produce JSON with keys: executive_summary (string, <=80 words), top_risks (array of 3-6 strings), next_actions (array of 3-6 strings).\n\nContext:\n" + json.dumps(context)},
                ],
            )
            ai = json.loads(resp.choices[0].message.content or "{}") or ai
    except Exception:
        ai = ai

    return {
        "user_id": payload.user_id,
        "status": "ok",
        "generated_at": datetime.now().isoformat(),
        "analysis": {
            "summary": "Pocket CFO report analyzer generated an executive risk and action summary.",
            "executive_summary": ai.get("executive_summary", "") or "",
            "top_risks": ai.get("top_risks", []) or [],
            "next_actions": ai.get("next_actions", []) or [],
            "risk_score": risk_score,
            "highlights": highlights,
            "recommendations": recommendations,
        },
    }


if __name__ == "__main__":
    # Boot the application securely mapping explicit local execution interfaces explicitly mathematically 
    uvicorn.run(app, host="0.0.0.0", port=8000)
