"""
Compliance engine services for Pocket CFO.

Implements hackathon-grade scaffolding for:
1) Account Aggregator (AA) FIU integration flow
2) MSME verification + Section 43B(h) payable aging checks
3) W-8BEN PDF + Form 15CA/15CB XML generation
4) Foreign SaaS OIDAR RCM detection + GST pre-flight checks
5) Compliance calendar reminders + DRL triggers
"""

from __future__ import annotations

import hashlib
import json
import os
import logging
import smtplib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest
from xml.etree.ElementTree import Element, SubElement, tostring
from bson.objectid import ObjectId

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from pocket_cfo_parser.db.mongo import (
    aa_consents_collection,
    aa_sessions_collection,
    compliance_calendar_collection,
    drl_requests_collection,
    foreign_remittances_collection,
    gst_preflight_collection,
    payables_collection,
    transactions_collection,
    users_collection,
    vendors_collection,
)

logger = logging.getLogger(__name__)


def _normalize_iso_date(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text).date().isoformat()
        except ValueError:
            return None
    return None


def _compliance_mode() -> str:
    """Select compliance integration mode from environment (mock/live)."""
    return os.getenv("COMPLIANCE_MODE", "mock").strip().lower()


def _resolve_user_email(user_id: str) -> str | None:
    """Resolve reminder recipient email from user profile or fallback env."""
    user_doc = None
    try:
        user_doc = users_collection.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user_doc = users_collection.find_one({"_id": user_id})
    if not user_doc:
        user_doc = users_collection.find_one({"user_id": user_id})
    email = (user_doc or {}).get("email") if isinstance(user_doc, dict) else None
    if isinstance(email, str) and email.strip():
        return email.strip()
    fallback = os.getenv("REMINDER_EMAIL_TO", "").strip()
    return fallback or None


def _send_email_reminder(recipient: str, subject: str, body: str) -> tuple[bool, str]:
    """Send reminder email via SMTP using environment configuration."""
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_FROM_EMAIL", username).strip()
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}

    logger.info(f"Email send attempt: to={recipient}, from={sender}, host={host}, use_tls={use_tls}")

    if not (host and sender and recipient):
        msg = f"SMTP not configured (host={bool(host)}, sender={bool(sender)}, recipient={bool(recipient)})"
        logger.warning(f"Email skipped: {msg}")
        return False, msg

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        logger.info(f"Connecting to SMTP {host}:{port}...")
        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                logger.info("Starting TLS...")
                server.starttls()
            if username and password:
                logger.info(f"Logging in as {username}...")
                server.login(username, password)
            logger.info(f"Sending email to {recipient}...")
            server.send_message(msg)
        logger.info(f"Email sent successfully to {recipient}")
        return True, "sent"
    except smtplib.SMTPAuthenticationError as exc:
        logger.error(f"SMTP auth failed: {exc}")
        return False, f"auth error: {exc}"
    except Exception as exc:
        logger.exception(f"Failed to send email to {recipient}: {exc}")
        return False, f"error: {exc}"





# -----------------------------
# Phase 1: AA FIU flow
# -----------------------------

AA_STATUSES = {"PENDING", "ACTIVE", "REJECTED", "REVOKED", "EXPIRED", "PAUSED"}


def create_aa_consent(user_id: str, aa_handle: str, fi_types: list[str], from_date: str, to_date: str) -> dict:
    consent_id = f"consent-{uuid.uuid4().hex[:16]}"
    consent_handle = f"handle-{uuid.uuid4().hex[:12]}"
    redirect_url = f"https://aa.mock/consent/{consent_id}"
    doc = {
        "user_id": user_id,
        "consent_id": consent_id,
        "consent_handle": consent_handle,
        "aa_handle": aa_handle,
        "status": "PENDING",
        "fi_types": fi_types,
        "data_range": {"from": from_date, "to": to_date},
        "created_at": datetime.now().isoformat(),
    }
    aa_consents_collection.update_one({"consent_id": consent_id}, {"$set": doc}, upsert=True)
    aa_sessions_collection.update_one(
        {"consent_id": consent_id},
        {"$set": {"user_id": user_id, "consent_id": consent_id, "data_status": "PENDING", "fetch_attempts": 0}},
        upsert=True,
    )
    return {"consent_id": consent_id, "consent_handle": consent_handle, "redirect_url": redirect_url}


def update_aa_consent_status(consent_id: str, status: str, payload: dict | None = None) -> dict:
    status_norm = status.upper()
    if status_norm not in AA_STATUSES:
        status_norm = "PENDING"
    aa_consents_collection.update_one(
        {"consent_id": consent_id},
        {"$set": {"status": status_norm, "last_webhook": payload or {}, "updated_at": datetime.now().isoformat()}},
        upsert=True,
    )
    return {"consent_id": consent_id, "status": status_norm}


def mark_aa_data_ready(consent_id: str, session_id: str, payload: dict | None = None) -> dict:
    aa_sessions_collection.update_one(
        {"consent_id": consent_id},
        {
            "$set": {
                "consent_id": consent_id,
                "session_id": session_id,
                "data_status": "READY",
                "raw_meta": payload or {},
                "updated_at": datetime.now().isoformat(),
            }
        },
        upsert=True,
    )
    return {"consent_id": consent_id, "session_id": session_id, "data_status": "READY"}


def _hash_payload(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def fetch_aa_financial_data(consent_id: str, session_id: str, user_id: str) -> dict:
    mode = _compliance_mode()
    if mode == "live":
        provider_base = os.getenv("AA_PROVIDER_BASE_URL", "").strip()
        if not provider_base:
            raise RuntimeError("COMPLIANCE_MODE=live requires AA_PROVIDER_BASE_URL")
        logger.info("AA live mode enabled but provider fetch is not implemented; using webhook payload only.")

    session_doc = aa_sessions_collection.find_one({"consent_id": consent_id}) or {}
    raw_meta = session_doc.get("raw_meta") or {}
    seed_rows = raw_meta.get("transactions") if isinstance(raw_meta, dict) else None
    if not seed_rows:
        seed_rows = [
            {"date": datetime.now().date().isoformat(), "amount": 13250.0, "type": "debit", "party": "AWS Singapore", "fi_type": "DEPOSIT"},
            {"date": datetime.now().date().isoformat(), "amount": 85400.0, "type": "credit", "party": "Customer NEFT", "fi_type": "DEPOSIT"},
            {"date": datetime.now().date().isoformat(), "amount": 15750.0, "type": "debit", "party": "Slack Billing", "fi_type": "DEPOSIT"},
        ]
    upserted = 0
    for row in seed_rows:
        payload_hash = _hash_payload(row)
        tx_doc = {
            "user_id": user_id,
            "amount": row["amount"],
            "type": row["type"],
            "party": row["party"],
            "date": row["date"],
            "source": "aa",
            "raw_text": f"AA:{row['party']}",
            "category": "General Business Expense" if row["type"] == "debit" else "Sales Income",
            "sub_category": "AA Import",
            "business_nature": "business",
            "confidence": 0.99,
            "aa": {
                "enabled": True,
                "consent_id": consent_id,
                "session_id": session_id,
                "fi_type": row["fi_type"],
                "verified": True,
                "integration_mode": mode,
                "fetched_at": datetime.now().isoformat(),
                "payload_hash": payload_hash,
                "raw": row,
            },
        }
        transactions_collection.update_one(
            {"user_id": user_id, "aa.payload_hash": payload_hash},
            {"$setOnInsert": tx_doc},
            upsert=True,
        )
        upserted += 1

    aa_sessions_collection.update_one(
        {"consent_id": consent_id},
        {"$set": {"data_status": "FETCHED", "fetched_at": datetime.now().isoformat()}, "$inc": {"fetch_attempts": 1}},
        upsert=True,
    )
    return {
        "consent_id": consent_id,
        "session_id": session_id,
        "integration_mode": mode,
        "upserted_transactions": upserted,
    }


# -----------------------------
# Phase 2: MSME + 43B(h)
# -----------------------------

def verify_msme_vendor(user_id: str, vendor_name: str, pan: str, udyam_number: str | None = None) -> dict:
    mode = _compliance_mode()
    if mode == "live" and not os.getenv("MSME_PROVIDER_API_KEY"):
        raise RuntimeError("COMPLIANCE_MODE=live requires MSME_PROVIDER_API_KEY")

    enterprise_type = "MICRO" if vendor_name.lower().startswith(("micro", "nano")) else "SMALL"
    record = {
        "user_id": user_id,
        "name": vendor_name,
        "pan": pan.upper(),
        "udyam_number": udyam_number or "",
        "has_written_agreement": False,
        "agreed_credit_days": None,
        "msme": {
            "verified": True,
            "enterprise_type": enterprise_type,
            "registration_date": "2021-04-01",
            "active_status": "ACTIVE",
            "source": "live-msme-api" if mode == "live" else "mock-msme-api",
            "integration_mode": mode,
            "fetched_at": datetime.now().isoformat(),
        },
    }
    vendors_collection.update_one({"user_id": user_id, "pan": pan.upper()}, {"$set": record}, upsert=True)
    return record


def create_payable_invoice(user_id: str, vendor_pan: str, invoice_number: str, invoice_date: str, amount: float) -> dict:
    vendor = vendors_collection.find_one({"user_id": user_id, "pan": vendor_pan.upper()})
    if not vendor:
        raise ValueError("Vendor not found. Verify MSME vendor first.")

    threshold_days = 45 if vendor.get("has_written_agreement") else 15
    msme_type = vendor.get("msme", {}).get("enterprise_type", "UNKNOWN")
    applicable = msme_type in {"MICRO", "SMALL"} and vendor.get("msme", {}).get("verified", False)

    inv_doc = {
        "user_id": user_id,
        "vendor_id": str(vendor.get("_id")),
        "vendor_pan": vendor_pan.upper(),
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "amount": amount,
        "amount_paid": 0.0,
        "status": "OPEN",
        "section_43bh": {
            "applicable": applicable,
            "threshold_days": threshold_days if applicable else None,
            "breached": False,
            "deduction_disallowance_flag": False,
        },
        "created_at": datetime.now().isoformat(),
    }
    payables_collection.update_one(
        {"user_id": user_id, "invoice_number": invoice_number, "vendor_pan": vendor_pan.upper()},
        {"$set": inv_doc},
        upsert=True,
    )
    return inv_doc


def run_43bh_aging(user_id: str) -> dict:
    now = datetime.now()
    cursor = payables_collection.find({"user_id": user_id, "status": {"$in": ["OPEN", "PART_PAID"]}})
    flagged = []
    for inv in cursor:
        sec = inv.get("section_43bh", {})
        if not sec.get("applicable"):
            continue
        threshold_days = int(sec.get("threshold_days") or 45)
        invoice_date = datetime.fromisoformat(inv["invoice_date"])
        age_days = (now - invoice_date).days
        breached = age_days > threshold_days
        if breached:
            payables_collection.update_one(
                {"_id": inv["_id"]},
                {"$set": {"section_43bh.breached": True, "section_43bh.deduction_disallowance_flag": True}},
            )
            flagged.append(
                {
                    "invoice_number": inv.get("invoice_number"),
                    "vendor_pan": inv.get("vendor_pan"),
                    "age_days": age_days,
                    "threshold_days": threshold_days,
                    "alert": "Potential deduction disallowance under Section 43B(h).",
                }
            )
    return {"user_id": user_id, "flagged_count": len(flagged), "alerts": flagged}


# -----------------------------
# Phase 3: W-8BEN + Form 15CA XML
# -----------------------------

@dataclass
class W8BENData:
    full_name: str
    registered_address: str
    pan: str
    country: str = "India"


def generate_w8ben_pdf(data: W8BENData, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = f"w8ben_{data.pan}_{uuid.uuid4().hex[:8]}.pdf"
    full_path = os.path.join(output_dir, filename)

    c = canvas.Canvas(full_path, pagesize=A4)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, 800, "W-8BEN (Individual) - Pocket CFO Draft")
    c.setFont("Helvetica", 11)
    c.drawString(40, 770, f"Line 1 - Name: {data.full_name}")
    c.drawString(40, 750, f"Line 2 - Country of citizenship: {data.country}")
    c.drawString(40, 730, f"Line 3 - Permanent residence address: {data.registered_address}")
    c.drawString(40, 710, f"Line 6a - Foreign TIN (PAN): {data.pan}")
    c.drawString(40, 680, "Generated for DTAA treaty claim support workflow.")
    c.showPage()
    c.save()
    return full_path


def generate_form_15ca_xml(remittance: dict[str, Any]) -> str:
    root = Element("Form15CA")
    remitter = SubElement(root, "Remitter")
    SubElement(remitter, "Name").text = str(remittance.get("remitter_name", ""))
    SubElement(remitter, "PAN").text = str(remittance.get("remitter_pan", ""))

    remittee = SubElement(root, "Remittee")
    SubElement(remittee, "Name").text = str(remittance.get("remittee_name", ""))
    SubElement(remittee, "Country").text = str(remittance.get("remittee_country", ""))

    payment = SubElement(root, "Payment")
    SubElement(payment, "AmountINR").text = str(remittance.get("amount_inr", 0))
    SubElement(payment, "PurposeCode").text = str(remittance.get("purpose_code", "P0802"))
    SubElement(payment, "DTAAApplicable").text = str(bool(remittance.get("dtaa_applicable", True))).lower()
    SubElement(payment, "Taxability").text = str(remittance.get("taxability", "TAXABLE"))
    SubElement(payment, "WithholdingRate").text = str(remittance.get("withholding_rate", 0))

    xml_bytes = tostring(root, encoding="utf-8")
    return xml_bytes.decode("utf-8")


def generate_form_15cb_xml(remittance: dict[str, Any]) -> str:
    """Generates the XML schema for Form 15CB (CA Certificate) required for remittances > 5 Lakhs."""
    root = Element("Form15CB")
    ca_details = SubElement(root, "CACredentials")
    SubElement(ca_details, "MembershipNumber").text = "MOCK-CA-12345"
    SubElement(ca_details, "FirmRegistrationNumber").text = "FRN-987654"
    SubElement(ca_details, "DateOfCertificate").text = datetime.now().date().isoformat()
    
    remitter = SubElement(root, "Remitter")
    SubElement(remitter, "Name").text = str(remittance.get("remitter_name", ""))
    SubElement(remitter, "PAN").text = str(remittance.get("remitter_pan", ""))

    remittee = SubElement(root, "Remittee")
    SubElement(remittee, "Name").text = str(remittance.get("remittee_name", ""))
    SubElement(remittee, "Country").text = str(remittance.get("remittee_country", ""))

    payment = SubElement(root, "Payment")
    SubElement(payment, "AmountINR").text = str(remittance.get("amount_inr", 0))
    SubElement(payment, "PurposeCode").text = str(remittance.get("purpose_code", "P0802"))
    
    dtaa_applicable = bool(remittance.get("dtaa_applicable", True))
    SubElement(payment, "DTAAApplicable").text = str(dtaa_applicable).lower()
    
    # 15CB specific DTAA details
    if dtaa_applicable:
        dtaa_details = SubElement(payment, "DTAADetails")
        SubElement(dtaa_details, "TreatyArticle").text = "Article 12 (Royalties and FTS)" if "software" in str(remittance.get("purpose_code", "")).lower() else "Article 7 (Business Profits)"
        SubElement(dtaa_details, "TRCProvided").text = "true"

    SubElement(payment, "Taxability").text = str(remittance.get("taxability", "TAXABLE"))
    SubElement(payment, "WithholdingRate").text = str(remittance.get("withholding_rate", 0))

    xml_bytes = tostring(root, encoding="utf-8")
    return xml_bytes.decode("utf-8")


def save_foreign_remittance(user_id: str, remittance: dict[str, Any]) -> dict:
    doc = {"user_id": user_id, **remittance, "created_at": datetime.now().isoformat()}
    foreign_remittances_collection.insert_one(doc)
    
    amount = float(remittance.get("amount_inr", 0))
    needs_forms = amount > 500000
    
    xml_15ca = generate_form_15ca_xml(remittance) if needs_forms else ""
    xml_15cb = generate_form_15cb_xml(remittance) if needs_forms else ""
    
    return {
        "saved": True, 
        "needs_form_15ca_15cb": needs_forms, 
        "xml_15ca": xml_15ca,
        "xml_15cb": xml_15cb
    }


# -----------------------------
# Phase 4: OIDAR + RCM + pre-flight
# -----------------------------

FOREIGN_SAAS_KEYS = {"aws", "slack", "github", "notion", "atlassian", "openai", "google cloud", "azure", "stripe"}


def detect_oidar_rcm(party: str, amount: float) -> dict:
    lower = (party or "").lower()
    matched = any(key in lower for key in FOREIGN_SAAS_KEYS)
    if not matched:
        return {"oidar_import": False, "rcm_applicable": False, "rcm_rate": 0.0, "igst_rcm_liability": 0.0}
    liability = round(float(amount) * 0.18, 2)
    return {
        "oidar_import": True,
        "rcm_applicable": True,
        "rcm_rate": 18.0,
        "igst_rcm_liability": liability,
        "classification": "Import of OIDAR services",
    }


def run_gst_preflight(gstr1_total_tax: float, gstr3b_total_tax: float, user_id: str) -> dict:
    diff = round(float(gstr1_total_tax) - float(gstr3b_total_tax), 2)
    blocked = abs(diff) > 1.0
    result = {
        "user_id": user_id,
        "gstr1_total_tax": float(gstr1_total_tax),
        "gstr3b_total_tax": float(gstr3b_total_tax),
        "difference": diff,
        "blocked": blocked,
        "message": "Submission blocked due to mismatch." if blocked else "Pre-flight passed.",
        "created_at": datetime.now().isoformat(),
    }
    gst_preflight_collection.insert_one(result)
    return result


# -----------------------------
# Phase 5: DRL + MCA scheduler
# -----------------------------

MCA_FORMS_BY_ENTITY = {
    "pvt_ltd": ["AOC-4", "MGT-7"],
    "llp": ["Form-11", "Form-8"],
    "opc": ["AOC-4", "MGT-7A"],
}


def get_deadline_penalty_insights(form_code: str) -> str:
    """Use OpenAI to generate insights on penalties for missing a specific compliance deadline."""
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"Standard late fee of ₹50-200 per day applies for {form_code} under relevant acts."
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You are a strict Indian Chartered Accountant. Give a 1-2 sentence warning about the exact penalty, interest, or consequence of missing the filing deadline for the given form. Be specific with sections (e.g. 234A/B/C, late fees)."},
                {"role": "user", "content": f"Form: {form_code}"}
            ]
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return f"Standard late fee applies for {form_code}."


def _next_advance_tax_due(anchor_date: datetime) -> str:
    """Return the next advance-tax due date after the anchor date."""
    cycle = [
        datetime(anchor_date.year, 6, 15),
        datetime(anchor_date.year, 9, 15),
        datetime(anchor_date.year, 12, 15),
        datetime(anchor_date.year + 1, 3, 15),
    ]
    for due in cycle:
        if due.date() >= anchor_date.date():
            return due.date().isoformat()
    return datetime(anchor_date.year + 1, 6, 15).date().isoformat()


def schedule_compliance_calendar(
    user_id: str,
    entity_type: str,
    financial_year_end: str,
    basis_date: str | None = None,
) -> dict:
    forms = MCA_FORMS_BY_ENTITY.get(entity_type.lower(), ["AOC-4", "MGT-7"])
    anchor = datetime.now()
    if basis_date:
        try:
            anchor = datetime.fromisoformat(basis_date)
        except Exception:
            anchor = datetime.now()

    # Build monthly deadlines from the month implied by extracted transaction data.
    period_month_start = anchor.replace(day=1)
    next_month = (period_month_start + timedelta(days=32)).replace(day=1)
    
    standard_forms = [
        {"code": "GSTR-1", "due_date": next_month.replace(day=11).date().isoformat()},
        {"code": "GSTR-3B", "due_date": next_month.replace(day=20).date().isoformat()},
        {"code": "TDS Payment", "due_date": next_month.replace(day=7).date().isoformat()},
        {"code": "Advance Tax", "due_date": _next_advance_tax_due(anchor)}
    ]
    
    fy_end = datetime.fromisoformat(financial_year_end)
    due_base = fy_end + timedelta(days=180)
    
    for f in forms:
        standard_forms.append({"code": f, "due_date": due_base.date().isoformat()})
        
    reminders = []
    for form in standard_forms:
        due_date_obj = datetime.fromisoformat(form["due_date"])
        # Add penalty insights
        penalty_insight = get_deadline_penalty_insights(form["code"])
        
        for offset in [15, 3, 0]:
            reminders.append(
                {
                    "form_code": form["code"],
                    "due_date": form["due_date"],
                    "reminder_date": (due_date_obj - timedelta(days=offset)).date().isoformat(),
                    "offset_days": offset,
                    "penalty_insight": penalty_insight
                }
            )
            
    doc = {
        "user_id": user_id,
        "entity_type": entity_type,
        "financial_year_end": financial_year_end,
        "basis_date": anchor.date().isoformat(),
        "reminders": reminders,
        "sent_notification_keys": [],
        "last_notified_at": None,
        "created_at": datetime.now().isoformat(),
    }
    compliance_calendar_collection.update_one({"user_id": user_id}, {"$set": doc}, upsert=True)
    return doc


def trigger_deadline_notifications(user_id: str, run_date: str | None = None, send_all_pending: bool = False) -> dict:
    """
    Trigger WhatsApp mock alerts plus optional email reminders.
    
    Args:
        user_id: Target user ID
        run_date: Override today's date (ISO format)
        send_all_pending: If True, send all reminders with reminder_date <= today (useful on first schedule)
    """
    doc = compliance_calendar_collection.find_one({"user_id": user_id})
    if not doc:
        logger.warning(f"No compliance calendar found for user {user_id}")
        return {"status": "no_calendar"}

    today = datetime.now().date().isoformat()
    if run_date:
        try:
            today = datetime.fromisoformat(run_date).date().isoformat()
        except Exception:
            today = datetime.now().date().isoformat()

    reminders_raw = doc.get("reminders", [])
    reminders = reminders_raw if isinstance(reminders_raw, list) else []
    if reminders_raw is not None and not isinstance(reminders_raw, list):
        logger.warning("Ignoring malformed reminders payload for user %s: expected list", user_id)

    sent_keys_raw = doc.get("sent_notification_keys", [])
    sent_keys: set[str] = set()
    ignored_sent_keys = 0
    if isinstance(sent_keys_raw, list):
        for item in sent_keys_raw:
            if isinstance(item, str):
                if item:
                    sent_keys.add(item)
            elif isinstance(item, (int, float, bool)):
                sent_keys.add(str(item))
            elif item is not None:
                ignored_sent_keys += 1
    elif sent_keys_raw not in (None, ""):
        ignored_sent_keys += 1

    if ignored_sent_keys > 0:
        logger.warning("Ignored %s malformed sent_notification_keys item(s) for user %s", ignored_sent_keys, user_id)

    recipient_email = _resolve_user_email(user_id)
    
    logger.info(f"Notification trigger: user={user_id}, today={today}, send_all_pending={send_all_pending}, email={recipient_email}")
    logger.info(f"Total reminders in calendar: {len(reminders)}")
    
    triggered = []
    email_sent = 0
    email_failed = 0
    skipped_invalid_reminders = 0
    reminders_due_today = 0

    for r in reminders:
        if not isinstance(r, dict):
            skipped_invalid_reminders += 1
            continue

        reminder_date = _normalize_iso_date(r.get("reminder_date"))
        if reminder_date is None:
            if r.get("reminder_date") is not None:
                skipped_invalid_reminders += 1
            continue

        if reminder_date == today:
            reminders_due_today += 1

        form_code = r.get("form_code")
        
        if send_all_pending:
            # Send all reminders with reminder_date <= today
            if reminder_date > today:
                continue
        else:
            # Send only reminders with reminder_date == today
            if reminder_date != today:
                continue
        
        logger.info(f"Processing reminder: {form_code} on {reminder_date}")

        reminder_key = f"{r.get('form_code')}|{r.get('due_date')}|{r.get('offset_days')}|{reminder_date}"
        if reminder_key in sent_keys:
            continue

        message = f"🚨 DEADLINE ALERT: {r.get('form_code')} is due on {r.get('due_date')}. {r.get('penalty_insight')}"

        detail = {
            "form": r.get("form_code"),
            "due_date": r.get("due_date"),
            "channel": "WhatsApp",
            "message": message,
        }

        if recipient_email:
            ok_email, email_info = _send_email_reminder(
                recipient=recipient_email,
                subject=f"Compliance Reminder: {r.get('form_code')} due {r.get('due_date')}",
                body=(
                    f"Hello,\n\n"
                    f"This is your Pocket CFO compliance reminder.\n"
                    f"Form: {r.get('form_code')}\n"
                    f"Due Date: {r.get('due_date')}\n"
                    f"Reminder Date: {reminder_date}\n"
                    f"Penalty Insight: {r.get('penalty_insight')}\n\n"
                    f"Regards,\nPocket CFO"
                ),
            )
            detail["email"] = {"sent": ok_email, "recipient": recipient_email, "info": email_info}
            logger.info(f"Email result for {form_code}: sent={ok_email}, info={email_info}")
            if ok_email:
                email_sent += 1
                sent_keys.add(reminder_key)
            else:
                email_failed += 1
        else:
            detail["email"] = {"sent": False, "recipient": None, "info": "No user email or REMINDER_EMAIL_TO configured"}
            logger.warning(f"No email configured for reminder {form_code}")

        triggered.append(detail)

    compliance_calendar_collection.update_one(
        {"user_id": user_id},
        {"$set": {"sent_notification_keys": sorted(sent_keys), "last_notified_at": datetime.now().isoformat()}},
        upsert=True,
    )

    if skipped_invalid_reminders > 0:
        logger.warning("Skipped %s malformed reminder item(s) for user %s", skipped_invalid_reminders, user_id)
    
    logger.info(f"Notification summary: triggered={len(triggered)}, email_sent={email_sent}, email_failed={email_failed}")
            
    return {
        "user_id": user_id,
        "run_date": today,
        "notifications_sent": len(triggered),
        "email_sent": email_sent,
        "email_failed": email_failed,
        "details": triggered,
        "already_notified": max(0, reminders_due_today - len(triggered)),
    }


def generate_ca_report_pdf(user_id: str, report_data: dict, output_dir: str) -> str:
    """Generates a professional, formatted CA report as a PDF using ReportLab, styled like actual CA reports."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"CA_Report_{user_id}_{uuid.uuid4().hex[:6]}.pdf"
    full_path = os.path.join(output_dir, filename)

    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.units import inch

    doc = SimpleDocTemplate(full_path, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  # Center
        textColor=colors.darkblue
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkgreen
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=20,
        spaceAfter=5
    )

    story = []

    # Title Page
    story.append(Paragraph("CHARTERED ACCOUNTANT'S REPORT", title_style))
    story.append(Spacer(1, 0.5*inch))
    
    story.append(Paragraph(f"<b>Client ID:</b> {user_id}", normal_style))
    story.append(Paragraph(f"<b>Report Date:</b> {datetime.now().strftime('%d %B %Y')}", normal_style))
    story.append(Paragraph(f"<b>Period:</b> Financial Year {datetime.now().year - 1}-{datetime.now().year}", normal_style))
    story.append(Spacer(1, 1*inch))
    
    story.append(Paragraph("This report has been prepared based on the financial transactions provided and is intended for informational purposes only. Please consult with a qualified Chartered Accountant for professional advice.", normal_style))
    story.append(PageBreak())

    # Executive Summary
    story.append(Paragraph("EXECUTIVE SUMMARY", header_style))
    
    profit = report_data.get("summary", {})
    data = [
        ["Metric", "Amount (₹)"],
        ["Total Revenue", f"{profit.get('total_revenue', 0):,.2f}"],
        ["Total Expenses", f"{profit.get('total_expenses', 0):,.2f}"],
        ["Net Profit", f"{profit.get('net_profit', 0):,.2f}"],
        ["Profit Margin", f"{profit.get('profit_margin', 0):.1f}%"],
        ["Potential Monthly Tax Savings", f"{profit.get('potential_monthly_savings', 0):,.2f}"],
        ["Claimable ITC", f"{profit.get('claimable_itc', 0):,.2f}"],
        ["GST Payable", f"{profit.get('gst_payable', 0):,.2f}"],
        ["Taxable Income", f"{profit.get('taxable_income', 0):,.2f}"],
    ]
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5*inch))

    # Key Findings
    story.append(Paragraph("KEY FINDINGS", header_style))
    findings = [
        f"• The business generated ₹{profit.get('total_revenue', 0):,.2f} in revenue during the period.",
        f"• Net profit stands at ₹{profit.get('net_profit', 0):,.2f}, representing a {profit.get('profit_margin', 0):.1f}% margin.",
        f"• Potential monthly tax savings of ₹{profit.get('potential_monthly_savings', 0):,.2f} identified.",
        f"• ₹{profit.get('claimable_itc', 0):,.2f} in Input Tax Credit is available for claim.",
        f"• Reconciliation issues: {profit.get('reconciliation_issues', {}).get('summary', {}).get('low_confidence_count', 0)} low-confidence transactions.",
        f"• Audit flags: {profit.get('audit_flags', {}).get('suspicious_transactions_count', 0)} suspicious transactions identified.",
    ]
    
    for finding in findings:
        story.append(Paragraph(finding, bullet_style))
    
    story.append(PageBreak())

    # Detailed Analysis
    story.append(Paragraph("DETAILED ANALYSIS", header_style))
    
    # GST Compliance
    story.append(Paragraph("GST Compliance Status", styles['Heading3']))
    gst_data = report_data.get("detailed_breakdown", {}).get("gst_compliance", {}).get("report", {}).get("gstr_3b", {}).get("section_3_net_payable", {})
    gst_table_data = [
        ["GST Component", "Amount (₹)"],
        ["Output GST Liability", f"{gst_data.get('total_tax_liability', 0):,.2f}"],
        ["ITC Available", f"{gst_data.get('total_itc_available', 0):,.2f}"],
        ["Net GST Payable", f"{gst_data.get('net_gst_payable', 0):,.2f}"],
        ["Refund Available", f"{gst_data.get('net_refund_available', 0):,.2f}"],
    ]
    
    gst_table = Table(gst_table_data)
    gst_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(gst_table)
    story.append(Spacer(1, 0.3*inch))

    # Income Tax
    story.append(Paragraph("Income Tax Estimate", styles['Heading3']))
    tax_data = report_data.get("detailed_breakdown", {}).get("income_tax", {})
    tax_table_data = [
        ["Tax Component", "Amount (₹)"],
        ["Taxable Income", f"{tax_data.get('taxable_income_summary', {}).get('taxable_income', 0):,.2f}"],
        ["Tax Liability", f"{tax_data.get('tax_liability', {}).get('total_tax_liability', 0):,.2f}"],
    ]
    
    tax_table = Table(tax_table_data)
    tax_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(tax_table)
    story.append(Spacer(1, 0.3*inch))

    # Action Items
    story.append(Paragraph("RECOMMENDED ACTIONS", header_style))
    actions = report_data.get("action_items", [])
    if not isinstance(actions, list):
        actions = []
    if actions:
        for action in actions[:10]:  # Limit to top 10
            if not isinstance(action, dict):
                continue
            priority = str(action.get('priority', 'info')).upper()
            color_name = 'red' if priority == 'HIGH' or priority == 'RED' else 'orange' if priority in {'AMBER', 'MEDIUM'} else 'green'
            story.append(Paragraph(f"<font color='{color_name}'>[{priority}]</font> {action.get('title', '')}", bullet_style))
            story.append(Paragraph(f"   {action.get('message', '')}", bullet_style))
            story.append(Spacer(1, 0.1*inch))
    else:
        story.append(Paragraph("No critical action items identified.", normal_style))

    story.append(Spacer(1, 1*inch))
    story.append(Paragraph("<i>This report is generated by AI and should be reviewed by a qualified Chartered Accountant before taking any action.</i>", normal_style))
    story.append(Paragraph(f"<b>Generated by Pocket CFO on {datetime.now().strftime('%d/%m/%Y at %H:%M')}</b>", normal_style))

    doc.build(story)
    return full_path


def get_compliance_calendar_events(user_id: str) -> dict:
    """Returns compliance deadlines in a calendar-friendly format for UI display."""
    doc = compliance_calendar_collection.find_one({"user_id": user_id})
    if not doc:
        return {"user_id": user_id, "events": [], "message": "No calendar scheduled. Use /compliance/calendar/auto/{user_id} to create one."}
    
    reminders = doc.get("reminders", [])
    events = []
    for r in reminders:
        events.append({
            "id": f"{r['form_code']}_{r['due_date']}_{r['offset_days']}",
            "title": f"{r['form_code']} Deadline",
            "start": r["reminder_date"],
            "description": f"Reminder ({r['offset_days']}d before). Due: {r['due_date']}. {r['penalty_insight']}",
            "category": "reminder",
            "priority": "high" if r["offset_days"] == 0 else "medium" if r["offset_days"] == 3 else "low",
            "form_code": r["form_code"],
            "reminder_date": r["reminder_date"],
            "due_date": r["due_date"],
            "penalty_insight": r["penalty_insight"]
        })
    
    return {"user_id": user_id, "events": events, "total_events": len(events)}


def trigger_drl_if_missing_invoice(user_id: str, threshold_amount: float = 20000.0) -> dict:
    cursor = transactions_collection.find({"user_id": user_id, "type": "debit", "amount": {"$gte": threshold_amount}})
    triggered = []
    for txn in cursor:
        # invoice_file_id intentionally optional - triggers DRL when missing
        if txn.get("invoice_file_id"):
            continue
        req_id = f"drl-{uuid.uuid4().hex[:10]}"
        drl_doc = {
            "request_id": req_id,
            "user_id": user_id,
            "transaction_ref": str(txn.get("_id")),
            "party": txn.get("party", "Unknown"),
            "amount": txn.get("amount", 0.0),
            "status": "PENDING_UPLOAD",
            "upload_link": f"https://pocketcfo.local/upload/{req_id}",
            "created_at": datetime.now().isoformat(),
        }
        drl_requests_collection.update_one({"request_id": req_id}, {"$set": drl_doc}, upsert=True)
        triggered.append(drl_doc)
    return {"user_id": user_id, "drl_triggered_count": len(triggered), "requests": triggered}
