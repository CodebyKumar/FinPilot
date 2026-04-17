import logging
from langchain_core.tools import tool
from typing import Dict, Any

from finpilot.agents.expense_agent import get_expense_summary
from finpilot.agents.profit_agent import get_profit_summary
from finpilot.agents.reconciliation_agent import get_reconciliation_report
from finpilot.agents.bookkeeping_agent import get_bookkeeping_summary
from finpilot.db.mongo import get_transactions_by_user

logger = logging.getLogger(__name__)

@tool
def analyze_expenses(user_id: str) -> Dict[str, Any]:
    """Use this tool to get an analysis of the user's expenses, categorizations, and identification of spending outliers."""
    txns = get_transactions_by_user(user_id)
    return get_expense_summary(txns)

@tool
def analyze_profits(user_id: str) -> Dict[str, Any]:
    """Use this tool to calculate operating net profits, revenue vs costs, and profit margins."""
    txns = get_transactions_by_user(user_id)
    return get_profit_summary(txns)

@tool
def run_reconciliation(user_id: str) -> Dict[str, Any]:
    """Use this tool to check for duplicate transactions, mismatched balances, and general ledger errors."""
    txns = get_transactions_by_user(user_id)
    return get_reconciliation_report(txns)

@tool
def get_bookkeeping_ledgers(user_id: str) -> Dict[str, Any]:
    """Use this tool to retrieve a breakdown of journal entries and general ledger structures."""
    txns = get_transactions_by_user(user_id)
    return get_bookkeeping_summary(txns)
