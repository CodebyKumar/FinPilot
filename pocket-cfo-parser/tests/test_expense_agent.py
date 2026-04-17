"""
Tests for the Expense Agent logic mapping and analytics processing limits.
Validates exact variance boundaries mathematically isolating outlier values conditionally.
"""

from datetime import datetime
from pocket_cfo_parser.models.transaction import Transaction
from pocket_cfo_parser.agents.expense_agent import (
    categorize_expenses,
    detect_anomalies,
    get_expense_summary
)


def make_txn(party: str, amount: float, txn_type: str = "debit") -> Transaction:
    """Helper method to dynamically instantiate populated isolate Transactions cleanly."""
    return Transaction(
        amount=amount,
        type=txn_type, # type: ignore
        party=party,
        date=datetime.now(),
        source="sms",
        raw_text=f"Mock data transaction involving {party} {amount}"
    )


def test_categorize_expenses_groups_correctly():
    # Pass 3 debit transactions logically segregating 2 dynamic rules engines implicitly
    txns = [
        make_txn("Swiggy", 200.0),
        make_txn("Zomato", 300.0),
        make_txn("Airtel", 590.0)
    ]
    
    result = categorize_expenses(txns)
    
    # Assert by_category has at least 2 keys 
    assert len(result["by_category"]) >= 2
    
    # Assert mathematical bounds aggregate sum perfectly
    assert result["total_expenses"] == 1090.0


def test_categorize_excludes_credits():
    # Evaluating strict mapping bounding inclusions solely handling debit operations
    txns = [
        make_txn("Swiggy", 200.0, "debit"),
        make_txn("Infosys", 5000.0, "credit")
    ]
    
    result = categorize_expenses(txns)
    
    # Assert mathematically isolates and executes exactly the single debit expense
    assert result["total_expenses"] == 200.0
    assert result["transaction_count"] == 1


def test_top_category_identified():
    txns = [
        make_txn("Swiggy", 200.0),
        make_txn("Zomato", 300.0),
        make_txn("Zomato", 400.0)
    ]
    
    result = categorize_expenses(txns)
    
    # Assert top_category correctly dynamically assigns volume sum maximum tracking
    assert "Food" in result["top_category"]


def test_detect_anomalies_flags_outlier():
    # Structural variance test verifying standard deviation multiplier mapping boundaries
    txns = [
        make_txn("Airtel", 500.0),
        make_txn("Airtel", 520.0),
        make_txn("Airtel", 510.0),
        make_txn("Airtel", 490.0),
        make_txn("Airtel", 5000.0)
    ]
    
    anomalies = detect_anomalies(txns)
    
    # Assert at least 1 anomaly is fundamentally mapped via high variances limits
    assert len(anomalies) >= 1
    
    # Find matching amounts explicitly validating parsing bounds isolation accuracy
    assert any(a["transaction"]["amount"] == 5000.0 for a in anomalies)
    assert any("median_amount" in a for a in anomalies)


def test_detect_anomalies_requires_three_samples():
    txns = [
        make_txn("Airtel", 500.0),
        make_txn("Airtel", 5000.0)
    ]
    
    anomalies = detect_anomalies(txns)
    
    # Assert anomalies list safely circumvents mathematical boundaries limits explicitly natively
    assert len(anomalies) == 0


def test_get_expense_summary_structure():
    # Provide fully unstructured sequential pipeline context directly asserting structural keys formats
    txns = [
        make_txn("Airtel", 590.0),
        make_txn("Amazon", 1000.0),
        make_txn("Swiggy", 300.0),
        make_txn("Infosys", 5000.0, "credit")
    ]
    
    result = get_expense_summary(txns)
    
    # Check that structural dictionary definitions fundamentally correspond natively sequentially
    expected_keys = [
        "categories", 
        "total_expenses", 
        "top_category", 
        "anomalies", 
        "anomaly_count", 
        "insight"
    ]
    
    for key in expected_keys:
        assert key in result


def test_insight_string_format():
    txns = [
        make_txn("Swiggy", 200.0),
        make_txn("Zomato", 300.0),
        make_txn("Zomato", 400.0)
    ]
    
    result = get_expense_summary(txns)
    insight = result.get("insight", "")
    
    # Validate accurate symbol assignments implicitly injected inside formatted string metrics parameters
    assert "₹" in insight
    assert "transactions" in insight
