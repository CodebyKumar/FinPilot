from __future__ import annotations

from fastapi import APIRouter, HTTPException

from finpilot.schemas.modules import ProfileCreateRequest, ProfileBase
from finpilot.services.execute_service import (
    create_profile,
    get_profile,
    update_profile,
    delete_profile,
)

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.post("/create")
def create_profile_route(payload: ProfileCreateRequest):
    try:
        data = create_profile(payload.user_id, payload.model_dump(exclude={"user_id"}))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{user_id}")
def get_profile_route(user_id: str):
    try:
        data = get_profile(user_id)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{user_id}")
def update_profile_route(user_id: str, payload: ProfileBase):
    try:
        data = update_profile(user_id, payload.model_dump(exclude_unset=True))
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{user_id}")
def delete_profile_route(user_id: str):
    try:
        data = delete_profile(user_id)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
