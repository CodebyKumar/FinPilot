from __future__ import annotations

import asyncio
from datetime import datetime
import logging

from finpilot import config
from finpilot.db.mongo import _get_db
from finpilot.services.gmail_service import resolve_user_email, send_email

logger = logging.getLogger(__name__)


def _deadlines_collection():
    return _get_db()["deadlines"]


def _notifications_collection():
    return _get_db()["notifications"]


def _jobs_collection():
    return _get_db()["jobs"]


def _now_iso() -> str:
    return datetime.now().isoformat()


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


def scan_deadlines_once(user_id: str | None = None, force_queue: bool = False) -> int:
    now = datetime.now()
    created = 0
    windows = {7, 1, 0}

    query: dict = {
        "status": {"$in": ["pending", "scheduled", None]},
        "submitted": {"$ne": True},
    }
    if user_id:
        query["user_id"] = user_id

    deadlines = list(
        _deadlines_collection().find(
            query,
            {"_id": 0},
        )
    )

    for item in deadlines:
        due_date = _parse_date(item.get("due_date"))
        if due_date is None:
            continue

        days = _days_left(due_date, now)
        if not force_queue and days not in windows:
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


def _notification_subject(notification: dict) -> str:
    title = notification.get("title") or "Compliance deadline"
    due_date = notification.get("due_date") or "-"
    return f"Compliance Reminder: {title} (Due {due_date})"


def _notification_body(notification: dict) -> str:
    return (
        "Hello,\n\n"
        "This is a compliance reminder from FinPilot.\n"
        f"- Title: {notification.get('title', 'Compliance deadline')}\n"
        f"- Type: {notification.get('type', 'compliance')}\n"
        f"- Due Date: {notification.get('due_date', '-')}\n"
        f"- Days Left: {notification.get('days_left', '-')}\n\n"
        "Please complete the filing before the due date.\n\n"
        "Regards,\nFinPilot"
    )


def dispatch_queued_notifications(limit: int = 50, user_id: str | None = None) -> int:
    query: dict = {"status": "queued"}
    if user_id:
        query["user_id"] = user_id

    queued = list(
        _notifications_collection().find(
            query,
            {"_id": 0},
        ).sort("created_at", 1).limit(limit)
    )

    sent_count = 0
    for item in queued:
        notification_key = item.get("notification_key")
        user_id = item.get("user_id")
        recipient = resolve_user_email(str(user_id or "")) if user_id else None

        if not recipient:
            _notifications_collection().update_one(
                {"notification_key": notification_key},
                {
                    "$set": {
                        "status": "failed",
                        "error": "No recipient email found",
                        "updated_at": _now_iso(),
                    }
                },
            )
            continue

        email_result = send_email(
            recipient=recipient,
            subject=_notification_subject(item),
            body=_notification_body(item),
        )

        if email_result.get("sent"):
            sent_count += 1
            _notifications_collection().update_one(
                {"notification_key": notification_key},
                {
                    "$set": {
                        "status": "sent",
                        "recipient": recipient,
                        "sent_at": _now_iso(),
                        "updated_at": _now_iso(),
                    }
                },
            )
        else:
            _notifications_collection().update_one(
                {"notification_key": notification_key},
                {
                    "$set": {
                        "status": "failed",
                        "recipient": recipient,
                        "error": email_result.get("info", "email send failed"),
                        "updated_at": _now_iso(),
                    }
                },
            )

    return sent_count


async def run_deadline_worker(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            created = scan_deadlines_once()
            sent = dispatch_queued_notifications()
            if created or sent:
                logger.info("Deadline worker queued %d and sent %d notifications", created, sent)
        except Exception as exc:
            logger.error("Deadline worker failure: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=config.DEADLINE_SCAN_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue
