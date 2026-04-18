from __future__ import annotations

from fastapi import APIRouter, HTTPException

from finpilot.schemas.modules import DeadlineAddRequest
from finpilot.services.execute_service import deadline_add, deadline_get, deadline_delete

router = APIRouter(prefix="/deadline", tags=["Deadline"])


@router.post("/add")
def add_deadline_route(payload: DeadlineAddRequest):
    try:
        data = deadline_add(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{user_id}")
def get_deadline_route(user_id: str):
    try:
        data = deadline_get(user_id)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{deadline_id}")
def delete_deadline_route(deadline_id: str, user_id: str):
    try:
        data = deadline_delete(user_id, deadline_id)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
