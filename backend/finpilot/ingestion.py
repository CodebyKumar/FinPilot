"""
Unified ingestion layer for FinPilot.

Single entry point for data ingestion workflows.
Each ingested record is classified by the GST agent before being persisted.
"""

import logging

from finpilot.models.transaction import Transaction
from finpilot.parsers.pdf_parser import parse_pdf
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


def ingest_pdf(filepath: str, user_id: str) -> list[Transaction]:
    """
    Parse and persist all transactions from a bank statement PDF.
    Returns the list of saved Transaction objects.
    """
    results = parse_pdf(filepath)
    for txn in results:
        _apply_classification(txn)
        save_transaction(txn, user_id)
    logger.info("PDF ingestion: saved %d transactions for user %s", len(results), user_id)
    return results
