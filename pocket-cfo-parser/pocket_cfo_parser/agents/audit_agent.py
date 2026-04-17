"""
Audit Agent

Validates transactions, detects anomalies, and flags suspicious entries.
"""

import statistics
from collections import defaultdict
from datetime import datetime
from pocket_cfo_parser.models.transaction import Transaction


def validate_gst_consistency(txn: Transaction) -> dict:
    gst_rate = getattr(txn, "gst_rate", 0.0) or 0.0
    gst_amount = getattr(txn, "gst_amount", None)
    calculated_gst = txn.amount * gst_rate / (100.0 + gst_rate) if gst_rate else 0.0
    expected_gst = round(calculated_gst, 2)
    issues = []

    if gst_amount is None:
        issues.append("GST amount missing")
    elif round(gst_amount, 2) != expected_gst:
        issues.append(f"GST amount mismatch: expected ₹{expected_gst}, found ₹{gst_amount}")

    if txn.itc_eligible and getattr(txn, "itc_amount", 0.0) < expected_gst - 1e-2:
        issues.append("ITC eligible but ITC amount appears understated")

    if txn.itc_eligible and getattr(txn, "business_nature", "business") == "personal":
        issues.append("Personal transaction marked ITC eligible")

    return {
        "transaction_id": txn.id,
        "issues": issues,
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "expected_gst_amount": expected_gst
    }


def detect_suspicious_transactions(transactions: list[Transaction]) -> list[dict]:
    if not transactions:
        return []

    suspicious = []
    debit_amounts = [txn.amount for txn in transactions if txn.type == "debit"]
    if len(debit_amounts) >= 2:
        mean = statistics.mean(debit_amounts)
        stdev = statistics.stdev(debit_amounts) if len(debit_amounts) > 1 else 0.0
    else:
        mean = stdev = 0.0

    grouped = defaultdict(list)
    for txn in transactions:
        key = (txn.party.strip().lower(), round(txn.amount, 2), txn.type)
        grouped[key].append(txn)

    for key, txns in grouped.items():
        if len(txns) > 3:
            suspicious.append({
                "issue": "Repeated identical transaction pattern",
                "party": key[0],
                "amount": key[1],
                "type": key[2],
                "count": len(txns),
                "transactions": [txn.to_dict() for txn in txns[:4]]
            })

    for txn in transactions:
        if txn.type == "debit" and stdev > 0 and txn.amount > mean + 3 * stdev:
            suspicious.append({
                "issue": "High debit outlier",
                "transaction": txn.to_dict(),
                "average_debit": round(mean, 2),
                "std_dev": round(stdev, 2)
            })

        if txn.confidence < 0.4:
            suspicious.append({
                "issue": "Low classification confidence",
                "transaction": txn.to_dict()
            })

        if txn.category is None or txn.category.lower() in {"uncategorized", "other"}:
            suspicious.append({
                "issue": "Uncategorized transaction",
                "transaction": txn.to_dict()
            })

    return suspicious


def get_audit_report(transactions: list[Transaction]) -> dict:
    gst_validation = [validate_gst_consistency(txn) for txn in transactions if txn.type in {"debit", "credit"}]
    gst_issues = [item for item in gst_validation if item["issues"]]
    suspicious = detect_suspicious_transactions(transactions)

    return {
        "report_type": "Audit & Validation Report",
        "generated_at": datetime.now().isoformat(),
        "gst_validation_issues": gst_issues,
        "suspicious_transactions": suspicious,
        "summary": {
            "gst_issues_count": len(gst_issues),
            "suspicious_transactions_count": len(suspicious)
        },
        "recommendations": [
            "Resolve GST mismatches before filing returns.",
            "Investigate repeated or outlier transactions for potential data quality issues.",
            "Verify low-confidence parsed entries against source documents."
        ]
    }
