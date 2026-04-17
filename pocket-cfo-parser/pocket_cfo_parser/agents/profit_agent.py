"""
Profit Agent
Calculates the real profit of a business chronologically aggregating revenue, 
operational expenses, mapped structural GST deductions, and ITC claims safely.
"""

from pocket_cfo_parser.models.transaction import Transaction
from pocket_cfo_parser.agents.gst_agent import analyze_itc_opportunities

def calculate_profit(transactions: list[Transaction]) -> dict:
    """
    Computes volumetric limits segregating gross profit schemas from
    total revenues iteratively evaluating claimable Input Tax Credits mathematically.
    """
    total_revenue = 0.0
    total_expenses = 0.0
    total_gst_paid = 0.0
    
    revenue_count = 0
    expense_count = 0
    
    for txn in transactions:
        if txn.type == "credit":
            total_revenue += txn.amount
            revenue_count += 1
        elif txn.type == "debit":
            total_expenses += txn.amount
            expense_count += 1
            total_gst_paid += getattr(txn, "gst_amount", 0.0)
            
    # Derive core business operational bounds natively
    gross_profit = total_revenue - total_expenses
    
    # Run the ITC analytical engine natively locating recoverable credit injections
    itc_analysis = analyze_itc_opportunities(transactions)
    total_itc_claimable = itc_analysis.get("total_itc_claimable", 0.0)
    
    # Net logic: Extracted ITC effectively offsets expenditure tax boundaries improving final returns mathematically
    net_profit = gross_profit + total_itc_claimable
    
    # Deduce chronological tax efficiency structures structurally safely checking zeroes
    effective_tax_rate = 0.0
    if total_revenue > 0:
        effective_tax_rate = (total_gst_paid / total_revenue) * 100.0
        
    return {
        "total_revenue": round(total_revenue, 2),
        "total_expenses": round(total_expenses, 2),
        "gross_profit": round(gross_profit, 2),
        "total_gst_paid": round(total_gst_paid, 2),
        "total_itc_claimable": round(total_itc_claimable, 2),
        "net_profit": round(net_profit, 2),
        "effective_tax_rate": round(effective_tax_rate, 2),
        "revenue_transactions": revenue_count,
        "expense_transactions": expense_count
    }

def get_profit_summary(transactions: list[Transaction]) -> dict:
    """
    Formulates a globally accessible dashboard representation merging exact structural 
    evaluations with dynamically generated English intelligence schemas mapping financial health bounds.
    """
    profit_data = calculate_profit(transactions)
    
    net = profit_data["net_profit"]
    
    # Define primary financial trajectory logic mapping explicit bounds natively 
    if net > 0:
        verdict = f"Profitable — you made ₹{net:,.2f} after expenses and GST recovery"
    elif net == 0:
        verdict = "Break even — revenue exactly covers expenses"
    else:
        verdict = f"Loss — you are ₹{abs(net):,.2f} short this period. Review your top expenses."
        
    itc = profit_data["total_itc_claimable"]
    
    # Tip algorithms
    if itc > 0:
        itc_tip = f"You can recover ₹{itc:,.2f} in GST credits — file your ITC claims to improve cashflow"
    else:
        itc_tip = "No ITC opportunities found this period"
        
    # Inject intelligence descriptors structurally back into the operational dict explicitly mapped 
    profit_data["verdict"] = verdict
    profit_data["itc_tip"] = itc_tip
    
    return profit_data
