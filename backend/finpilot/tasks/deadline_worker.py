from __future__ import annotations

import asyncio
from datetime import datetime
import logging

from finpilot import config
from finpilot.db.mongo import _get_db

logger = logging.getLogger(__name__)


def _deadlines_collection():
    return _get_db()["deadlines"]


def _notifications_collection():
    return _get_db()["notifications"]


def _jobs_collection():
    return _get_db()["jobs"]


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _days_left(due_date: datetime, now: datetime) -> int:
    return (due_date.date() - now.date()).days


def _submitted_report_ids(user_id: str) -> set[str]:
    reports = _get_db()["reports"].find(
        {"user_id": user_id, "status": "submitted"},
        {"_id": 0, "report_id": 1},
    )
    return {r.get("report_id") for r in reports if r.get("report_id")}


def scan_deadlines_once() -> int:
    now = datetime.now()
    created = 0
    windows = {7, 1, 0}

    deadlines = list(
        _deadlines_collection().find(
            {
                "status": {"$in": ["pending", "scheduled", None]},
                "submitted": {"$ne": True},
            },
            {"_id": 0},
        )
    )

    for item in deadlines:
        due_date = _parse_date(item.get("due_date"))
        if due_date is None:
            continue

        days = _days_left(due_date, now)
        if days not in windows:
            continue

        report_id = item.get("meta", {}).get("report_id")
        if report_id and report_id in _submitted_report_ids(item.get("user_id", "")):
            continue

        deadline_id = item.get("deadline_id")
        if not deadline_id:
            continue

        notification_key = f"{deadline_id}:{days}:{now.date().isoformat()}"
        notification = {
            "notification_key": notification_key,
            "user_id": item.get("user_id"),
            "deadline_id": deadline_id,
            "title": item.get("title", "Compliance deadline"),
            "type": item.get("type", "compliance"),
            "due_date": item.get("due_date"),
            "days_left": days,
            "channel": "gmail",
            "status": "queued",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = _notifications_collection().update_one(
            {"notification_key": notification_key},
            {"$setOnInsert": notification},
            upsert=True,
        )
        if result.upserted_id is not None:
            created += 1

    if created > 0:
        _jobs_collection().insert_one(
            {
                "job_id": f"deadline-scan-{now.isoformat()}",
                "task_name": "deadline_scan",
                "user_id": "system",
                "payload": {"notifications_created": created},
                "mode": "async",
                "status": "completed",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        )

    return created


async def run_deadline_worker(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            created = scan_deadlines_once()
            if created:
                logger.info("Deadline worker queued %d notifications", created)
        except Exception as exc:
            logger.error("Deadline worker failure: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=config.DEADLINE_SCAN_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue
