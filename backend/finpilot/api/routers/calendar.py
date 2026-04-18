from fastapi import APIRouter
from finpilot.services.calendar_engine import schedule_compliance_calendar, get_compliance_calendar_events
from finpilot.db.mongo import get_user

router = APIRouter(tags=["Calendar"])

@router.post("/calendar/auto/{user_id}")
def auto_schedule_calendar_route(user_id: str):
    """
    Auto-schedule compliance calendar from parsed transaction history / profile.
    """
    user = get_user(user_id) or {}
    entity_type = user.get("entity_type", "pvt_ltd")
    turnover = user.get("annual_turnover", 0.0)
    
    result = schedule_compliance_calendar(
        user_id=user_id,
        entity_type=entity_type,
        financial_year_end=None
    )
    
    return {
        "user_id": user_id,
        "message": "Calendar automatically scheduled based on business profile.",
        "calendar": result,
        "entity_used": entity_type
    }

@router.get("/calendar/events/{user_id}")
def get_compliance_calendar_events_route(user_id: str):
    """
    Returns compliance deadlines formatted as calendar events for UI display.
    """
    return get_compliance_calendar_events(user_id)
