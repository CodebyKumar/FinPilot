"""
Tests for the GST Agent classification logic and ITC calculations.
Validates exact deterministic mapping bounds and fallback API parameters.
"""

from datetime import datetime
from pocket_cfo_parser.models.transaction import Transaction
from pocket_cfo_parser.agents.gst_agent import classify_transaction, analyze_itc_opportunities

def create_mock_transaction(party: str, amount: float, txn_type: str = "debit") -> Transaction:
    """Helper method to dynamically instantiate populated isolated Transactions."""
    return Transaction(
        amount=amount,
        type=txn_type, # type: ignore
        party=party,
        date=datetime.now(),
        source="sms",
        raw_text=f"Mock data transaction involving {party}"
    )

def test_known_merchant_swiggy():
    # create a Transaction with party "Swiggy", amount 500.0, type "debit"
    txn = create_mock_transaction("Swiggy", 500.0, "debit")
    result = classify_transaction(txn)
    
    assert result["gst_rate"] == 5.0
    assert result["itc_eligible"] is False
    assert result["confidence"] == 0.9
    assert result["matched_rule"] == "swiggy"


def test_known_merchant_amazon():
    # party "Amazon Pay", amount 1000.0
    txn = create_mock_transaction("Amazon Pay", 1000.0, "debit")
    result = classify_transaction(txn)
    
    assert result["itc_eligible"] is True
    assert result["gst_rate"] == 18.0


def test_gst_amount_calculation():
    # party "Airtel", amount 118.0
    txn = create_mock_transaction("Airtel", 118.0, "debit")
    result = classify_transaction(txn)
    
    # Assert gst_amount is approximately 18.0 
    # back-calculation: 118 * 18 / 118 = 18.0
    assert abs(result["gst_amount"] - 18.0) < 0.01


def test_itc_amount_zero_for_ineligible():
    # party "Zomato", amount 200.0
    txn = create_mock_transaction("Zomato", 200.0, "debit")
    result = classify_transaction(txn)
    
    # Assert itc_amount == 0.0 because itc_eligible is False for Restaurant bills
    assert result["itc_amount"] == 0.0


def test_gemini_fallback_called_for_unknown():
    # party "Sharma General Store", amount 500.0
    txn = create_mock_transaction("Sharma General Store", 500.0, "debit")
    result = classify_transaction(txn)
    
    assert result is not None
    assert "category" in result
    assert "gst_rate" in result
    # It must evaluate to fallback constraints either globally resolving Gemini context implicitly (0.7)
    # or returning error containment fallback explicitly (0.4)
    assert result["confidence"] in [0.7, 0.4]


def test_analyze_itc_opportunities():
    # Create a list of 4 structured transactions
    txn1 = create_mock_transaction("Airtel", 590.0, "debit")
    txn2 = create_mock_transaction("Amazon", 1180.0, "debit")
    txn3 = create_mock_transaction("Swiggy", 200.0, "debit")
    
    # A credit transaction of ₹5000
    txn4 = create_mock_transaction("Investors Ltd", 5000.0, "credit")
    
    transactions = [txn1, txn2, txn3, txn4]
    
    result = analyze_itc_opportunities(transactions)
    
    # Verify accurate mathematical bounding exclusions based on state structures
    assert result["total_itc_claimable"] > 0
    # Expect 2 ITC transactions: only Airtel and Amazon are ITC eligible inherently mapped rules
    assert len(result["itc_transactions"]) == 2


def test_analyze_itc_summary_string():
    txn = create_mock_transaction("Delhivery Logistics", 1180.0, "debit")
    
    result = analyze_itc_opportunities([txn])
    summary = result.get("summary", "")
    
    # assert the summary string natively compiles valid UI structural templates implicitly containing symbols
    assert "Input Tax Credit" in summary
    assert "₹" in summary
