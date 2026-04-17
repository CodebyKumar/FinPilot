"""
Tests for the SMS parsing module using the sample SMS data.
"""

from datetime import datetime
from pocket_cfo_parser.parsers.sms_parser import parse_sms
from tests.test_data.sample_sms import SAMPLE_SMS

def test_hdfc_debit_parsed_correctly():
    # HDFC Bank - UPI Debit
    sms = SAMPLE_SMS[0]
    result = parse_sms(sms)
    
    assert result is not None
    assert result.type == "debit"
    assert result.amount == 250.0
    assert "Swiggy" in result.party

def test_sbi_multi_word_party_parsed_correctly():
    # SBI - UPI Debit (with multi-word party name and paisa amount)
    sms = SAMPLE_SMS[2]
    result = parse_sms(sms)
    
    assert result is not None
    assert "Raj Medical Store" in result.party
    assert result.amount == 1250.5

def test_icici_credit_parsed_correctly():
    # ICICI Bank - UPI Credit
    sms = SAMPLE_SMS[5]
    result = parse_sms(sms)
    
    assert result is not None
    assert result.type == "credit"
    assert result.amount == 12000.0

def test_kotak_debit_parsed_correctly():
    # Kotak Bank - UPI Debit
    sms = SAMPLE_SMS[14]
    result = parse_sms(sms)
    
    assert result is not None
    assert "Netflix" in result.party
    assert result.amount == 99.0

def test_failed_transaction_returns_none():
    # Failed/Declined transaction
    sms = SAMPLE_SMS[8]
    result = parse_sms(sms)
    
    assert result is None

def test_otp_message_returns_none():
    # OTP Message
    sms = SAMPLE_SMS[9]
    result = parse_sms(sms)
    
    assert result is None

def test_promotional_message_returns_none():
    # Promotional Message
    sms = SAMPLE_SMS[10]
    result = parse_sms(sms)
    
    assert result is None

def test_valid_transaction_fields_populated():
    # Take any valid transaction (e.g. HDFC Debit)
    sms = SAMPLE_SMS[0]
    result = parse_sms(sms)
    
    assert result is not None
    assert result.id is not None
    assert len(result.id) > 0
    assert result.source == "sms"
    assert isinstance(result.date, datetime)
