"""
Shared API dependencies.
"""

from datetime import datetime

from finpilot.models.transaction import Transaction
from finpilot.db.mongo import get_transactions_by_user


def fetch_user_transactions(user_id: str) -> list[Transaction]:
    """
    Retrieve and instantiate Transaction objects for a given user.
    Handles date deserialisation and provides robust defaults for missing fields.
    """
    raw_dicts = get_transactions_by_user(user_id)
    txns = []

    for r in raw_dicts:
        raw_date = r.get("date")
        if isinstance(raw_date, str):
            try:
                txn_date = datetime.fromisoformat(raw_date)
            except ValueError:
                txn_date = datetime.now()
        elif isinstance(raw_date, datetime):
            txn_date = raw_date
        else:
            txn_date = datetime.now()

        txn = Transaction(
            amount=r.get("amount", 0.0),
            type=r.get("type", "debit"),
            party=r.get("party", "Unknown"),
            date=txn_date,
            source=r.get("source", "sms"),
            category=r.get("category", "Uncategorized"),
            sub_category=r.get("sub_category", "Uncategorized"),
            business_nature=r.get("business_nature", "business"),
            gst_rate=r.get("gst_rate", 0.0),
            itc_eligible=r.get("itc_eligible", False),
            hsn_sac=r.get("hsn_sac", "UNKNOWN"),
            gst_amount=r.get("gst_amount", 0.0),
            itc_amount=r.get("itc_amount", 0.0),
            matched_rule=r.get("matched_rule", "none"),
            raw_text=r.get("raw_text", ""),
            confidence=r.get("confidence", 0.9),
        )
        txns.append(txn)

    return txns
