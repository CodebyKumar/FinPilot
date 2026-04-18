from __future__ import annotations

from fastapi import APIRouter, HTTPException

from finpilot.schemas.modules import AssistantChatRequest
from finpilot.services.execute_service import assistant_chat

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/chat")
def assistant_chat_route(payload: AssistantChatRequest):
    try:
        data = assistant_chat(payload.user_id, payload.message)
        return {"success": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
