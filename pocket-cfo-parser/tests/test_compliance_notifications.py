from datetime import datetime

import api.main as api_main
from pocket_cfo_parser import compliance_engine


class StubCollection:
    def __init__(self, doc=None):
        self.doc = doc
        self.last_update = None

    def find_one(self, _query):
        return self.doc

    def update_one(self, query, update, upsert=False):
        self.last_update = {
            "query": query,
            "update": update,
            "upsert": upsert,
        }

        class Result:
            upserted_id = None

        return Result()


def test_trigger_deadline_notifications_skips_unhashable_values(monkeypatch):
    calendar_doc = {
        "user_id": "u1",
        "reminders": [
            {
                "form_code": "GSTR-1",
                "due_date": "2026-05-11",
                "offset_days": 0,
                "reminder_date": "2026-05-01",
                "penalty_insight": "Late fee applies",
            },
            {
                "form_code": "TDS Payment",
                "due_date": "2026-05-07",
                "offset_days": 0,
                "reminder_date": datetime(2026, 5, 1),
                "penalty_insight": "Interest may apply",
            },
            {
                "form_code": "BROKEN",
                "due_date": "2026-05-12",
                "offset_days": 0,
                "reminder_date": {"bad": "value"},
                "penalty_insight": "Invalid reminder",
            },
            "invalid-reminder-row",
        ],
        "sent_notification_keys": [
            {"bad": "key"},
            "GSTR-1|2026-05-11|0|2026-05-01",
        ],
    }
    calendar_collection = StubCollection(calendar_doc)

    monkeypatch.setattr(compliance_engine, "compliance_calendar_collection", calendar_collection)
    monkeypatch.setattr(compliance_engine, "users_collection", StubCollection({"email": "owner@example.com"}))
    monkeypatch.setattr(compliance_engine, "_send_email_reminder", lambda *_args, **_kwargs: (True, "sent"))

    result = compliance_engine.trigger_deadline_notifications("u1", run_date="2026-05-01")

    assert result["notifications_sent"] == 1
    assert result["email_sent"] == 1
    assert result["already_notified"] == 1

    stored_keys = calendar_collection.last_update["update"]["$set"]["sent_notification_keys"]
    assert all(isinstance(key, str) for key in stored_keys)
    assert "GSTR-1|2026-05-11|0|2026-05-01" in stored_keys
    assert "TDS Payment|2026-05-07|0|2026-05-01" in stored_keys


def test_auto_schedule_route_ignores_malformed_reminder_dates(monkeypatch):
    call_history = []

    def fake_schedule_calendar(**_kwargs):
        return {
            "reminders": [
                {"reminder_date": {"nested": "object"}},
                {"reminder_date": "2026-05-10"},
                {"reminder_date": datetime(2026, 5, 9)},
            ]
        }

    def fake_trigger_notifications(user_id, run_date=None, send_all_pending=False):
        call_history.append({
            "user_id": user_id,
            "run_date": run_date,
            "send_all_pending": send_all_pending,
        })
        if send_all_pending:
            return {"notifications_sent": 0}
        return {"notifications_sent": 1, "run_date": run_date}

    monkeypatch.setattr(api_main, "_fetch_user_transactions", lambda _user_id: [])
    monkeypatch.setattr(api_main, "schedule_compliance_calendar", fake_schedule_calendar)
    monkeypatch.setattr(api_main, "trigger_deadline_notifications", fake_trigger_notifications)

    response = api_main.auto_schedule_calendar_from_transactions_route("u1")

    assert response["notification_mode"] == "forced_earliest"
    assert len(call_history) == 2
    assert call_history[0]["send_all_pending"] is True
    assert call_history[1]["run_date"] == "2026-05-09"
    assert response["notifications_triggered"]["run_date"] == "2026-05-09"
