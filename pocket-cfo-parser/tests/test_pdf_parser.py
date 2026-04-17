"""
Tests for the PDF parsing module using sample bank statement PDFs.
"""

import os
import pytest
from datetime import datetime
from pocket_cfo_parser.parsers.pdf_parser import parse_pdf

# Helper to resolve absolute path dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(BASE_DIR, "test_data")
HDFC_PDF_PATH = os.path.join(TEST_DATA_DIR, "hdfc_statement.pdf")
SBI_PDF_PATH = os.path.join(TEST_DATA_DIR, "sbi_statement.pdf")


def test_hdfc_pdf_returns_transactions():
    transactions = parse_pdf(HDFC_PDF_PATH)
    assert transactions is not None
    assert len(transactions) > 0


def test_hdfc_transaction_count():
    transactions = parse_pdf(HDFC_PDF_PATH)
    assert len(transactions) == 8


def test_hdfc_has_debit_and_credit():
    transactions = parse_pdf(HDFC_PDF_PATH)
    has_debit = any(txn.type == "debit" for txn in transactions)
    has_credit = any(txn.type == "credit" for txn in transactions)
    
    assert has_debit
    assert has_credit


def test_hdfc_salary_credit_found():
    transactions = parse_pdf(HDFC_PDF_PATH)
    
    salary_txn = None
    for txn in transactions:
        if txn.type == "credit" and "Infosys" in txn.party:
            salary_txn = txn
            break
            
    assert salary_txn is not None
    assert salary_txn.amount == 85000.0


def test_sbi_pdf_returns_transactions():
    transactions = parse_pdf(SBI_PDF_PATH)
    assert transactions is not None
    assert len(transactions) > 0


def test_sbi_transaction_count():
    transactions = parse_pdf(SBI_PDF_PATH)
    assert len(transactions) == 6


def test_all_transactions_have_required_fields():
    transactions = parse_pdf(HDFC_PDF_PATH)
    for txn in transactions:
        assert txn.id is not None
        assert len(txn.id) > 0
        assert txn.amount > 0
        assert txn.source == "pdf"
        assert isinstance(txn.date, datetime)


def test_invalid_filepath_returns_empty():
    # Calling with an invalid filepath should raise a FileNotFoundError natively
    with pytest.raises(FileNotFoundError):
        parse_pdf("nonexistent_file_path_12345.pdf")
