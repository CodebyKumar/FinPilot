"""
Tests for the unified Ingestion layer.
Validates the full parsing and MongoDB database flow.
"""

import os
import pytest
from bson.objectid import ObjectId
from tests.test_data.sample_sms import SAMPLE_SMS
from pocket_cfo_parser.ingestion import ingest_sms, ingest_pdf, ingest_batch_sms
from pocket_cfo_parser.db.mongo import save_user, get_transactions_by_user, transactions_collection, users_collection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(BASE_DIR, "test_data")
HDFC_PDF_PATH = os.path.join(TEST_DATA_DIR, "hdfc_statement.pdf")

@pytest.fixture(scope="module")
def test_user_id():
    """
    Creates a temporary test user in MongoDB.
    Teardown block deletes the test user's transactions and profile 
    from the database after all module tests execute to keep Atlas clean.
    """
    user_id = save_user("Test User", "9999999999", "Test Shop")
    
    yield user_id
    
    # Module-level Teardown cleanly sweeps the database
    if user_id:
        transactions_collection.delete_many({"user_id": user_id})
        try:
            users_collection.delete_one({"_id": ObjectId(user_id)})
        except Exception:
            pass


def test_ingest_single_sms(test_user_id):
    # Call ingest_sms with SAMPLE_SMS[0] (HDFC debit)
    result = ingest_sms(SAMPLE_SMS[0], test_user_id)
    
    assert result is not None
    assert result.id is not None
    assert len(result.id) > 0


def test_ingest_batch_sms(test_user_id):
    # Call ingest_batch_sms with the full SAMPLE_SMS list
    results = ingest_batch_sms(SAMPLE_SMS, test_user_id)
    
    # Assert at least 10 transactions come back (filtering out OTPs, promos, failures)
    assert len(results) >= 10


def test_ingest_pdf(test_user_id):
    # Call ingest_pdf with the HDFC PDF path
    results = ingest_pdf(HDFC_PDF_PATH, test_user_id)
    
    # Assert 8 transactions returned
    assert len(results) == 8


def test_transactions_saved_to_db(test_user_id):
    # Database queries checking earlier state
    db_transactions = get_transactions_by_user(test_user_id)
    
    # Assert the list is non-empty
    assert len(db_transactions) > 0


def test_duplicate_sms_not_saved_twice(test_user_id):
    sms_text = SAMPLE_SMS[0]
    
    # Call ingest_sms with SAMPLE_SMS[0] twice
    ingest_sms(sms_text, test_user_id)
    ingest_sms(sms_text, test_user_id)
    
    # Assert that transaction appears only once (upsert working correctly)
    db_transactions = get_transactions_by_user(test_user_id)
    
    # Since DB models are returned as dicts from pymongo, we use `.get`
    matching_txns = [txn for txn in db_transactions if txn.get("raw_text") == sms_text]
    
    assert len(matching_txns) == 1
