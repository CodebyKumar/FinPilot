from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Iterable

from finpilot import config
from finpilot.db.mongo import _get_db, get_user

logger = logging.getLogger(__name__)

Attachment = tuple[str, bytes, str]


def _profiles_collection():
    return _get_db()["profiles"]


def resolve_user_email(user_id: str) -> str | None:
    """Resolve recipient email from profile/users collections, then fallback env."""
    profile_doc = _profiles_collection().find_one(
        {"user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0, "personal_info": 1},
    ) or {}

    personal_info = profile_doc.get("personal_info")
    if isinstance(personal_info, dict):
        email = str(personal_info.get("email") or "").strip()
        if email:
            return email

    user_doc = get_user(user_id) or {}
    if isinstance(user_doc, dict):
        email = str(user_doc.get("email") or "").strip()
        if email:
            return email

    fallback = str(config.REMINDER_EMAIL_TO or "").strip()
    return fallback or None


def send_email(
    *,
    recipient: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    attachments: Iterable[Attachment] | None = None,
) -> dict:
    """Send an email using configured SMTP and return transport result."""
    host = str(config.SMTP_HOST or "").strip()
    port = int(config.SMTP_PORT)
    username = str(config.SMTP_USERNAME or "").strip()
    password = str(config.SMTP_PASSWORD or "").strip()
    sender = str(config.SMTP_FROM_EMAIL or username).strip()

    recipient = str(recipient or "").strip()
    if not (host and sender and recipient):
        info = (
            f"SMTP not configured (host={bool(host)}, sender={bool(sender)}, "
            f"recipient={bool(recipient)})"
        )
        logger.warning("Email skipped: %s", info)
        return {"sent": False, "recipient": recipient or None, "info": info}

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    for filename, data, mime in (attachments or []):
        maintype, subtype = "application", "octet-stream"
        if mime and "/" in mime:
            maintype, subtype = mime.split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            if config.SMTP_USE_TLS:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)

        logger.info("Email sent to %s", recipient)
        return {"sent": True, "recipient": recipient, "info": "sent"}
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("SMTP auth failed: %s", exc)
        return {"sent": False, "recipient": recipient, "info": f"auth error: {exc}"}
    except Exception as exc:
        logger.exception("Failed to send email")
        return {"sent": False, "recipient": recipient, "info": f"error: {exc}"}
