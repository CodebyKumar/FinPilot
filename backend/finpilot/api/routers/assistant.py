from __future__ import annotations

from fastapi import APIRouter, HTTPException

from finpilot.agents.orchestrator_agent import (
    get_orchestrator_graph_mermaid,
    get_orchestrator_graph_metadata,
)
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


@router.get("/graph")
def assistant_graph_route():
    try:
        return {
            "success": True,
            "data": {
                "format": "mermaid",
                "graph": get_orchestrator_graph_mermaid(),
                "metadata": get_orchestrator_graph_metadata(),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
