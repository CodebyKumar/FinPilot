"""
Tests for the Profit Agent logic processing.
Validates structural bounds isolating accounting aggregation limits natively explicitly. 
"""

from datetime import datetime
from pocket_cfo_parser.models.transaction import Transaction
from pocket_cfo_parser.agents.profit_agent import calculate_profit, get_profit_summary


def make_txn(party: str, amount: float, txn_type: str = "debit") -> Transaction:
    """Helper method mapping explicitly populated Transaction models safely natively."""
    return Transaction(
        amount=amount,
        type=txn_type, # type: ignore
        party=party,
        date=datetime.now(),
        source="sms",
        raw_text=f"Mock data transaction involving {party} {amount}"
    )


def test_calculate_profit_basic():
    # 1 credit Infosys 10000, 2 debits Swiggy 200 and Airtel 590
    txns = [
        make_txn("Infosys", 10000.0, "credit"),
        make_txn("Swiggy", 200.0, "debit"),
        make_txn("Airtel", 590.0, "debit")
    ]
    
    result = calculate_profit(txns)
    
    # Assert explicitly mathematically mapping baseline limits structurally 
    assert result["total_revenue"] == 10000.0
    assert result["total_expenses"] == 790.0
    assert result["gross_profit"] == 9210.0


def test_net_profit_includes_itc():
    txns = [
        make_txn("Infosys", 10000.0, "credit"),
        make_txn("Swiggy", 200.0, "debit"),
        make_txn("Airtel", 590.0, "debit")
    ]
    
    result = calculate_profit(txns)
    
    # Assert net_profit >= gross_profit conceptually proving ITC dynamically mapping recoveries
    assert result["net_profit"] >= result["gross_profit"]


def test_effective_tax_rate_calculated():
    txns = [
        make_txn("Infosys", 10000.0, "credit"),
        make_txn("Swiggy", 200.0, "debit"),
        make_txn("Airtel", 590.0, "debit")
    ]
    
    result = calculate_profit(txns)
    
    # Assert effectively bounded rate margins intrinsically mathematically percentages
    assert result["effective_tax_rate"] >= 0.0
    assert result["effective_tax_rate"] <= 100.0


def test_zero_revenue_no_crash():
    # pass only debit transactions implicitly pushing 0 denominator testing parameters safety mappings
    txns = [
        make_txn("Amazon", 5000.0, "debit"),
        make_txn("Airtel", 590.0, "debit")
    ]
    
    result = calculate_profit(txns)
    
    # Assert function doesn't crash isolating 0 states explicitly and assigning structural baseline 0 natively
    assert result["effective_tax_rate"] == 0.0


def test_loss_scenario():
    # 1 credit 500, 1 debit Amazon 5000 explicitly proving deduction maps
    txns = [
        make_txn("Infosys", 500.0, "credit"),
        make_txn("Amazon", 5000.0, "debit")
    ]
    
    result = calculate_profit(txns)
    
    # Assert negative boundaries mapped mathematically flawlessly isolating deficits explicitly
    assert result["gross_profit"] < 0


def test_get_profit_summary_has_verdict():
    txns = [
        make_txn("Infosys", 10000.0, "credit"),
        make_txn("Swiggy", 200.0, "debit")
    ]
    
    result = get_profit_summary(txns)
    
    assert "verdict" in result
    assert "itc_tip" in result


def test_profitable_verdict_string():
    txns = [
        make_txn("Infosys", 10000.0, "credit"),
        make_txn("Swiggy", 200.0, "debit")
    ]
    
    result = get_profit_summary(txns)
    
    assert "Profitable" in result["verdict"]


def test_loss_verdict_string():
    txns = [
        make_txn("Infosys", 500.0, "credit"),
        make_txn("Amazon", 5000.0, "debit")
    ]
    
    result = get_profit_summary(txns)
    
    assert "Loss" in result["verdict"]
