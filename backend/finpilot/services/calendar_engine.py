import os
from datetime import datetime, timedelta
import logging

from finpilot.db.mongo import get_compliance_calendar_collection

logger = logging.getLogger(__name__)

MCA_FORMS_BY_ENTITY = {
    "pvt_ltd": ["AOC-4", "MGT-7"],
    "pvt ltd": ["AOC-4", "MGT-7"],
    "llp": ["Form-11", "Form-8"],
    "sole proprietorship": ["Income Tax Return ITR-3/4"],
    "opc": ["AOC-4", "MGT-7A"],
}

def get_deadline_penalty_insights(form_code: str) -> str:
    """Use OpenAI to generate insights on penalties for missing a specific compliance deadline."""
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
    except Exception as exc:
        logger.error(f"Failed to fetch penalty insights for {form_code}: {exc}")
        return f"Standard late fee applies for {form_code}."

def schedule_compliance_calendar(user_id: str, entity_type: str, financial_year_end: str = None) -> dict:
    if not financial_year_end:
        now = datetime.now()
        financial_year_end = datetime(now.year if now.month <= 3 else now.year + 1, 3, 31).date().isoformat()

    forms = MCA_FORMS_BY_ENTITY.get(entity_type.lower(), ["AOC-4", "MGT-7"])
    
    now = datetime.now()
    next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    
    standard_forms = [
        {"code": "GSTR-1", "due_date": next_month.replace(day=11).date().isoformat()},
        {"code": "GSTR-3B", "due_date": next_month.replace(day=20).date().isoformat()},
        {"code": "TDS Payment", "due_date": next_month.replace(day=7).date().isoformat()},
        {"code": "Advance Tax", "due_date": datetime(now.year if now.month <= 3 else now.year + 1, 3, 15).date().isoformat()}
    ]
    
    fy_end = datetime.fromisoformat(financial_year_end)
    due_base = fy_end + timedelta(days=180)
    
    for f in forms:
        standard_forms.append({"code": f, "due_date": due_base.date().isoformat()})
        
    reminders = []
    for form in standard_forms:
        due_date_obj = datetime.fromisoformat(form["due_date"])
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
        "reminders": reminders,
        "created_at": datetime.now().isoformat(),
    }
    get_compliance_calendar_collection().update_one({"user_id": user_id}, {"$set": doc}, upsert=True)
    return doc

def get_compliance_calendar_events(user_id: str) -> dict:
    """Returns compliance deadlines in a calendar-friendly format for UI display."""
    doc = get_compliance_calendar_collection().find_one({"user_id": user_id})
    if not doc:
        return {"user_id": user_id, "events": [], "message": "No calendar scheduled. Use /calendar/auto/{user_id} to create one."}
    
    reminders = doc.get("reminders", [])
    events = []
    for r in reminders:
        events.append({
            "id": f"{r['form_code']}_{r['due_date']}_{r['offset_days']}",
            "title": f"{r['form_code']} Deadline",
            "start": r["due_date"],
            "description": f"Due: {r['due_date']}. {r['penalty_insight']}",
            "category": "deadline",
            "priority": "high" if r["offset_days"] == 0 else "medium" if r["offset_days"] == 3 else "low",
            "form_code": r["form_code"],
            "penalty_insight": r["penalty_insight"]
        })
    
    return {"user_id": user_id, "events": list({v['id']:v for v in events}.values()), "total_events": len(events)}
