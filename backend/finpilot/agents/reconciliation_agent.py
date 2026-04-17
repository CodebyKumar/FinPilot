"""
Reconciliation Agent

Detects duplicate entries, unexplained gaps in transaction dates, and
common bank reconciliation anomalies.
"""

from collections import defaultdict
from datetime import datetime

from finpilot.models.transaction import Transaction


def _normalize_transaction_key(txn: Transaction) -> tuple:
    return (
        txn.date.isoformat() if txn.date else "",
        round(txn.amount, 2),
        (txn.party or "").strip().lower(),
        txn.type,
    )


def find_duplicate_transactions(transactions: list[Transaction]) -> list[dict]:
    groups: dict = defaultdict(list)
    for txn in transactions:
        groups[_normalize_transaction_key(txn)].append(txn)

    duplicates = []
    for key, txns in groups.items():
        if len(txns) > 1:
            duplicates.append({
                "duplicate_key": {
                    "date":   key[0],
                    "amount": key[1],
                    "party":  key[2],
                    "type":   key[3],
                },
                "count":               len(txns),
                "transaction_ids":     [t.id for t in txns],
                "sample_transactions": [t.to_dict() for t in txns[:3]],
            })
    return duplicates


def detect_reconciliation_issues(transactions: list[Transaction]) -> dict:
    duplicates     = find_duplicate_transactions(transactions)
    uncategorized  = [
        t.to_dict() for t in transactions
        if not t.category or t.category.lower() in {"uncategorized", "other"}
    ]
    low_confidence = [t.to_dict() for t in transactions if t.confidence < 0.5]

    gap_alerts = []
    sorted_txns = sorted(transactions, key=lambda t: t.date)
    for i in range(1, len(sorted_txns)):
        prev = sorted_txns[i - 1]
        curr = sorted_txns[i]
        if (curr.date - prev.date).days > 30 and curr.type == "debit":
            gap_alerts.append({
                "message":       "Long transaction gap detected. Review monthly bank statements for missing entries.",
                "previous_date": prev.date.isoformat(),
                "current_date":  curr.date.isoformat(),
                "gap_days":      (curr.date - prev.date).days,
            })

    return {
        "duplicate_transactions":      duplicates,
        "uncategorized_transactions":  uncategorized,
        "low_confidence_transactions": low_confidence,
        "gap_alerts":                  gap_alerts,
        "summary": {
            "duplicate_count":      len(duplicates),
            "uncategorized_count":  len(uncategorized),
            "low_confidence_count": len(low_confidence),
            "gap_alert_count":      len(gap_alerts),
        },
    }


def get_reconciliation_report(transactions: list[Transaction], expected_balance: float | None = None) -> dict:
    issues = detect_reconciliation_issues(transactions)
    running = 0.0
    for txn in sorted(transactions, key=lambda t: t.date):
        running += txn.amount if txn.type == "credit" else -txn.amount

    recs = [
        "Review duplicate transactions before finalizing reconciliations.",
        "Resolve uncategorized debits and credits to improve statement matching.",
    ]
    if expected_balance is not None:
        recs.append("Use external bank statement totals where available to validate closing balance.")
    else:
        recs.append("Supply an expected closing balance for a complete reconciliation check.")

    return {
        "report_type":                "Bank Reconciliation Report",
        "generated_at":               datetime.now().isoformat(),
        "calculated_closing_balance": round(running, 2),
        "expected_closing_balance":   round(expected_balance, 2) if expected_balance is not None else None,
        "balance_difference":         round(running - expected_balance, 2) if expected_balance is not None else None,
        "issues":                     issues,
        "recommendations":            recs,
    }
