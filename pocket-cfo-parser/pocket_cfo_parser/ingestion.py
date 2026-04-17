"""
Unified Ingestion Layer for pocket-cfo-parser.

This module acts as the single entry point for all data ingestion workflows.
It interfaces directly with the parser endpoints (SMS, PDF) and strictly processes 
the outputs by communicating with the underlying MongoDB persistence layer.
"""

import logging
from pocket_cfo_parser.models.transaction import Transaction
from pocket_cfo_parser.parsers.sms_parser import parse_sms
from pocket_cfo_parser.parsers.pdf_parser import parse_pdf
from pocket_cfo_parser.db.mongo import save_transaction
from pocket_cfo_parser.agents.gst_agent import classify_transaction

# Set up logging to track ingestion status
logger = logging.getLogger(__name__)

def ingest_sms(text: str, user_id: str) -> Transaction | None:
    """
    Ingests a single SMS string.
    Parses the text and if a valid transaction is extracted, saves it to the database.
    """
    result = parse_sms(text)
    
    if result is not None:
        classification = classify_transaction(result)
        result.category = classification.get("category", "Uncategorized")
        result.sub_category = classification.get("sub_category", "Uncategorized")
        result.business_nature = classification.get("business_nature", "business")
        result.gst_rate = classification.get("gst_rate", 0.0)
        result.itc_eligible = classification.get("itc_eligible", False)
        result.hsn_sac = classification.get("hsn_sac", "UNKNOWN")
        result.gst_amount = classification.get("gst_amount", 0.0)
        result.itc_amount = classification.get("itc_amount", 0.0)
        result.matched_rule = classification.get("matched_rule", "none")
        if classification.get("confidence", 0) > result.confidence:
            result.confidence = classification["confidence"]
        save_transaction(result, user_id)
        logger.info(f"Successfully parsed and saved SMS transaction for user {user_id}")
    else:
        logger.debug(f"Skipped SMS message for user {user_id}: non-transactional or parse failure")
        
    return result

def ingest_pdf(filepath: str, user_id: str) -> list[Transaction]:
    """
    Ingests an entire bank statement PDF.
    Extracts all viable transactions and iteratively saves them to the database.
    """
    results = parse_pdf(filepath)
    
    saved_count = 0
    for txn in results:
        classification = classify_transaction(txn)
        txn.category = classification.get("category", "Uncategorized")
        txn.sub_category = classification.get("sub_category", "Uncategorized")
        txn.business_nature = classification.get("business_nature", "business")
        txn.gst_rate = classification.get("gst_rate", 0.0)
        txn.itc_eligible = classification.get("itc_eligible", False)
        txn.hsn_sac = classification.get("hsn_sac", "UNKNOWN")
        txn.gst_amount = classification.get("gst_amount", 0.0)
        txn.itc_amount = classification.get("itc_amount", 0.0)
        txn.matched_rule = classification.get("matched_rule", "none")
        if classification.get("confidence", 0) > txn.confidence:
            txn.confidence = classification["confidence"]
        save_transaction(txn, user_id)
        saved_count += 1
        
    logger.info(f"PDF Ingestion complete: Saved {saved_count} transactions for user {user_id}")
    return results

def ingest_batch_sms(messages: list[str], user_id: str) -> list[Transaction]:
    """
    Ingests a bulk list of SMS text messages.
    Automatically filters out failures and non-transactional texts.
    Returns all structurally parsed transactions sequentially.
    """
    transactions = []
    skipped_count = 0
    
    # 1. Takes a list of SMS strings
    for msg in messages:
        # 2. Calls ingest_sms for each one
        txn = ingest_sms(msg, user_id)
        
        # 3. Skips Nones
        if txn:
            transactions.append(txn)
        else:
            skipped_count += 1
            
    # Add logging for how many transactions were saved vs skipped
    logger.info(f"Batch SMS Ingestion complete: Saved {len(transactions)} transactions, Skipped {skipped_count} for user {user_id}")
    
    # 4. Returns all successfully parsed transactions as a list
    return transactions
