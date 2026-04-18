from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from langchain_core.tools import tool

from finpilot.db.mongo import get_agent_memories_collection


def _now_iso() -> str:
    return datetime.now().isoformat()


def save_agent_memory_data(
    user_id: str,
    key: str,
    value: Any,
    tags: list[str] | None = None,
) -> Dict[str, Any]:
    key_clean = str(key).strip()
    if not key_clean:
        return {"saved": False, "error": "key is required"}

    doc = {
        "user_id": user_id,
        "memory_key": key_clean,
        "value": value,
        "tags": tags or [],
        "updated_at": _now_iso(),
    }
    get_agent_memories_collection().update_one(
        {"user_id": user_id, "memory_key": key_clean},
        {"$set": doc},
        upsert=True,
    )
    return {"saved": True, "memory_key": key_clean, "user_id": user_id}


def recall_agent_memory_data(user_id: str, key: str | None = None, limit: int = 20) -> Dict[str, Any]:
    query: dict[str, Any] = {"user_id": user_id}
    if key:
        query["memory_key"] = str(key).strip()

    docs = list(
        get_agent_memories_collection()
        .find(query, {"_id": 0})
        .sort("updated_at", -1)
        .limit(max(1, min(int(limit), 100)))
    )
    return {
        "user_id": user_id,
        "count": len(docs),
        "items": docs,
    }


@tool
def save_agent_memory(
    user_id: str,
    key: str,
    value: Any,
    tags: list[str] | None = None,
) -> Dict[str, Any]:
    """Persist durable memory for the user that can be recalled by the orchestrator."""
    return save_agent_memory_data(user_id=user_id, key=key, value=value, tags=tags)


@tool
def recall_agent_memory(user_id: str, key: str | None = None, limit: int = 20) -> Dict[str, Any]:
    """Recall stored durable memory items for the user."""
    return recall_agent_memory_data(user_id=user_id, key=key, limit=limit)
