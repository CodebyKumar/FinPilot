"""
User and Profile Router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from finpilot.db.mongo import save_user, get_transactions_by_user
from finpilot.api.deps import fetch_user_transactions

router = APIRouter(tags=["Users"])


class UserCreatePayload(BaseModel):
    name: str
    phone: str
    business_name: str
    industry: str = "Unknown"
    entity_type: str = "Unknown"
    annual_turnover: float = 0.0


@router.post("/users/create")
def create_user_route(payload: UserCreatePayload):
    """Create or update a user profile in MongoDB."""
    user_id = save_user(
        payload.name, 
        payload.phone, 
        payload.business_name,
        payload.industry,
        payload.entity_type,
        payload.annual_turnover
    )
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return {"success": True, "backend_user_id": user_id}


@router.get("/users/{user_id}/profile")
def user_profile_route(user_id: str):
    """Get high-level contextual counts and context for a user profile."""
    from finpilot.db.mongo import get_user
    
    user = get_user(user_id) or {}
    txns = get_transactions_by_user(user_id)
    return {
        "user_id": user_id, 
        "transaction_count": len(txns),
        "business_name": user.get("business_name", "Unknown"),
        "industry": user.get("industry", "Unknown"),
        "entity_type": user.get("entity_type", "Unknown"),
        "annual_turnover": user.get("annual_turnover", 0.0),
    }

class UserProfielUpdatePayload(BaseModel):
    industry: str
    entity_type: str
    annual_turnover: float

@router.post("/users/{user_id}/profile")
def update_user_profile_route(user_id: str, payload: UserProfielUpdatePayload):
    from finpilot.db.mongo import _get_db
    from bson.objectid import ObjectId
    try:
        _get_db()["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "industry": payload.industry,
                "entity_type": payload.entity_type,
                "annual_turnover": payload.annual_turnover
            }}
        )
        return {"success": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/transactions/{user_id}", tags=["Transactions"])
def user_transactions_route(user_id: str):
    """Retrieve raw parsed chronological transaction records."""
    txns = fetch_user_transactions(user_id)
    sorted_txns = sorted(txns, key=lambda x: x.date, reverse=True)[:100]
    return {
        "transactions": [t.to_dict() for t in sorted_txns],
        "user_id": user_id,
    }
