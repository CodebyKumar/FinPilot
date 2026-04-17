"""
Expense Agent
Aggregates categorized expenses and dynamically detects spending anomalies natively 
leveraging standard deviation variance logic and categorical boundaries.
"""

import statistics
from pocket_cfo_parser.models.transaction import Transaction

def categorize_expenses(transactions: list[Transaction]) -> dict:
    """
    Groups and aggregates all expenses strictly by their corresponding GST categories.
    Determines average bounds and captures volumetric tracking globally.
    """
    by_category = {}
    total_business_expenses = 0.0
    total_personal_expenses = 0.0
    transaction_count = 0
    
    for txn in transactions:
        # Analytics solely processes deductive spending flows (expenses)
        if txn.type != "debit":
            continue
        
        category = txn.category or "Uncategorized"
        nature = txn.business_nature or "business"
        
        if category not in by_category:
            by_category[category] = {
                "total_spent": 0.0,
                "transaction_count": 0,
                "average_transaction": 0.0,
                "nature": nature,
                "transactions": []
            }
            
        by_category[category]["total_spent"] += txn.amount
        by_category[category]["transaction_count"] += 1
        by_category[category]["transactions"].append(txn.to_dict())
        
        if nature == "personal":
            total_personal_expenses += txn.amount
        else:
            total_business_expenses += txn.amount
        transaction_count += 1
        
    # Re-calculate averages mapping finalized bounded dimensions
    top_category = None
    max_spent = -1
    
    for cat, data in by_category.items():
        if data["transaction_count"] > 0:
            data["average_transaction"] = round(data["total_spent"] / data["transaction_count"], 2)
            
        # Round the aggregation bounds
        data["total_spent"] = round(data["total_spent"], 2)
        
        # Actively locate chronological top parameters structurally evaluating counts 
        if data["total_spent"] > max_spent:
            max_spent = data["total_spent"]
            top_category = cat
            
    return {
        "by_category": by_category,
        "total_business_expenses": round(total_business_expenses, 2),
        "total_personal_expenses": round(total_personal_expenses, 2),
        "total_expenses": round(total_business_expenses + total_personal_expenses, 2),
        "top_category": top_category,
        "transaction_count": transaction_count
    }

def detect_anomalies(transactions: list[Transaction]) -> list[dict]:
    """
    Detects unusual structural deviations spanning distinct categories systematically 
    leveraging standard deviations mathematically bounding variance limits globally.
    Flags occurrences surging 2+ Standard Deviations beyond average patterns.
    """
    by_category = {}
    
    # Stratify target amounts directly into chronological categorical buckets natively
    for txn in transactions:
        if txn.type != "debit":
            continue
            
        category = txn.category or "Uncategorized"
        party = txn.party.lower() if txn.party else ""
        group_key = f"{category}|{party}"
        
        if group_key not in by_category:
            by_category[group_key] = []
        by_category[group_key].append(txn)
        
    anomalies = []
    
    for group_key, txns in by_category.items():
        cat = group_key.split("|")[0]
        # Mathematical standards require at least 3 chronological samples resolving reliable variation natively 
        if len(txns) < 3:
            continue
            
        amounts = [t.amount for t in txns]
        median_amount = statistics.median(amounts)
        std_dev = statistics.stdev(amounts)
        
        # Prevent zero-variance constant crashing multiplier mappings structurally
        if std_dev == 0:
            continue
            
        # Deviation threshold bounds implicitly requiring limits passing 2 standard deviations continuously
        threshold = median_amount + (2 * std_dev)
        
        for txn in txns:
            if txn.amount > threshold:
                multiplier = round(txn.amount / median_amount, 1)
                
                # Format a plain English logical string structurally isolating outliers implicitly
                reason = f"{txn.party} payment of ₹{txn.amount:,.2f} is unusually high — {multiplier}x above your typical ₹{median_amount:,.2f}."
                
                anomalies.append({
                    "transaction": txn.to_dict(),
                    "category": cat,
                    "median_amount": round(median_amount, 2),
                    "std_dev": round(std_dev, 2),
                    "anomaly_reason": reason
                })
                
    return anomalies

def get_expense_summary(transactions: list[Transaction]) -> dict:
    """
    Unifies categorical stratifications and anomaly algorithms directly 
    returning cohesive diagnostic overviews globally mapping English insight strings natively.
    """
    # Sequentially invoke explicit sub-agent routines 
    categorized = categorize_expenses(transactions)
    anomalies = detect_anomalies(transactions)
    
    top_cat = categorized.get("top_category")
    
    # Fallback bounds 
    insight = "No valid expense data recorded or parsed this chronological period."
    
    # Compile a plain English structural overview logically mapping key observations 
    if top_cat:
        top_spent = categorized["by_category"][top_cat]["total_spent"]
        top_count = categorized["by_category"][top_cat]["transaction_count"]
        insight = f"Your highest spend this period is {top_cat} at ₹{top_spent:,.2f} across {top_count} transactions."
        
    return {
        "categories": categorized["by_category"],
        "total_expenses": categorized["total_expenses"],
        "top_category": top_cat,
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "insight": insight
    }
