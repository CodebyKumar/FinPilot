"""
Unified ingestion layer for FinPilot.

Single entry point for data ingestion workflows.
Each ingested record is classified by the GST agent before being persisted.
"""

import logging
from typing import Any

from finpilot.models.transaction import Transaction
from finpilot.services.parsers.statement_parser import parse_statement_file
from finpilot.db.mongo import save_transaction
from finpilot.agents.gst_agent import classify_transaction

logger = logging.getLogger(__name__)


def _apply_classification(txn: Transaction) -> None:
    """Enrich a transaction with GST classification in-place."""
    classification = classify_transaction(txn)
    txn.category       = classification.get("category",       "Uncategorized")
    txn.sub_category   = classification.get("sub_category",   "Uncategorized")
    txn.business_nature = classification.get("business_nature", "business")
    txn.gst_rate       = classification.get("gst_rate",       0.0)
    txn.itc_eligible   = classification.get("itc_eligible",   False)
    txn.hsn_sac        = classification.get("hsn_sac",        "UNKNOWN")
    txn.gst_amount     = classification.get("gst_amount",     0.0)
    txn.itc_amount     = classification.get("itc_amount",     0.0)
    txn.matched_rule   = classification.get("matched_rule",   "none")
    if classification.get("confidence", 0) > txn.confidence:
        txn.confidence = classification["confidence"]


def ingest_statement_with_stats(filepath: str, user_id: str) -> dict[str, Any]:
    """
    Parse and persist a bank statement file and return insertion stats.

    Notes:
    - parsed_count: transactions parsed from file
    - inserted_count: new rows inserted into ledger
    - duplicate_count: rows already present and skipped (upsert matched existing)
    - failed_count: rows that failed to persist
    """
    results = parse_statement_file(filepath)

    inserted: list[Transaction] = []
    duplicates: list[Transaction] = []
    inserted_count = 0
    duplicate_count = 0
    failed_count = 0

    for txn in results:
        _apply_classification(txn)
        write_result = save_transaction(txn, user_id)
        if write_result is None:
            failed_count += 1
            continue

        if getattr(write_result, "upserted_id", None) is not None:
            inserted_count += 1
            inserted.append(txn)
        else:
            duplicate_count += 1
            duplicates.append(txn)

    logger.info(
        "Statement ingestion: parsed=%d inserted=%d duplicate=%d failed=%d for user %s",
        len(results),
        inserted_count,
        duplicate_count,
        failed_count,
        user_id,
    )
    return {
        "transactions": results,
        "inserted_transactions": inserted,
        "duplicate_transactions": duplicates,
        "parsed_count": len(results),
        "inserted_count": inserted_count,
        "duplicate_count": duplicate_count,
        "failed_count": failed_count,
    }


def ingest_statement(filepath: str, user_id: str) -> list[Transaction]:
    """
    Parse and persist all transactions from a bank statement file.
    Returns the list of saved Transaction objects.
    """
    stats = ingest_statement_with_stats(filepath, user_id)
    transactions = stats.get("transactions")
    return transactions if isinstance(transactions, list) else []


def ingest_pdf_with_stats(filepath: str, user_id: str) -> dict[str, Any]:
    """Backward-compatible stats alias for statement ingestion."""
    return ingest_statement_with_stats(filepath, user_id)


def ingest_pdf(filepath: str, user_id: str) -> list[Transaction]:
    """Backward-compatible alias for statement ingestion."""
    return ingest_statement(filepath, user_id)
