import logging
from langchain_core.tools import tool
from typing import Dict, Any

from finpilot.agents.gst_agent import analyze_itc_opportunities
from finpilot.agents.tax_savings_agent import get_tax_insights
from finpilot.services.calendar_engine import get_compliance_calendar_events
from finpilot.db.mongo import get_transactions_by_user

logger = logging.getLogger(__name__)

@tool
def get_gst_itc_opportunities(user_id: str) -> Dict[str, Any]:
    """Use this tool to analyze the user's GST Input Tax Credit (ITC) opportunities, total claimable ITC, and missed ITC metrics."""
    logger.info("Executing get_gst_itc_opportunities for %s", user_id)
    txns = get_transactions_by_user(user_id)
    return analyze_itc_opportunities(txns)

@tool
def get_tax_planning_insights(user_id: str) -> Dict[str, Any]:
    """Use this tool to provide tax planning intelligence, potential tax savings, and quick achievable deductions."""
    logger.info("Executing get_tax_planning_insights for %s", user_id)
    txns = get_transactions_by_user(user_id)
    return get_tax_insights(txns)

@tool
def get_user_calendar_deadlines(user_id: str) -> dict:
    """Use this tool to see the user's upcoming compliance and tax deadlines, the forms required, and penalty consequences."""
    logger.info("Executing get_user_calendar_deadlines for %s", user_id)
    return get_compliance_calendar_events(user_id)
