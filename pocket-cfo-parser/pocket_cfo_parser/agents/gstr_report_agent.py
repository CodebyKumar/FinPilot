"""
GSTR Report Agent - GST Compliance Reports

Generates:
- GSTR-1 (Outward supplies) draft
- GSTR-3B (Monthly return) draft
- ITC summary
- HSN-wise summary
- Filing checklist
"""

from collections import defaultdict
from datetime import datetime
from pocket_cfo_parser.models.transaction import Transaction


def generate_gstr1_draft(transactions: list[Transaction]) -> dict:
    """
    GSTR-1 = Outward Supplies (what you sold/provided)
    Typically credit transactions in a business context.
    """
    outward_supplies = defaultdict(lambda: {
        "transactions": [],
        "total_value": 0.0,
        "total_gst": 0.0
    })
    
    for txn in transactions:
        if txn.type == "credit":  # Revenue/sales
            hsn_sac = getattr(txn, "hsn_sac", "NA") or "NA"
            gst_rate = getattr(txn, "gst_rate", 0.0)
            
            gst_amount = (txn.amount * gst_rate) / 100
            
            outward_supplies[hsn_sac]["transactions"].append({
                "date": txn.date.strftime("%d-%m-%Y"),
                "description": txn.party,
                "amount": round(txn.amount, 2),
                "gst_rate": gst_rate,
                "gst_amount": round(gst_amount, 2)
            })
            
            outward_supplies[hsn_sac]["total_value"] += txn.amount
            outward_supplies[hsn_sac]["total_gst"] += gst_amount
    
    # Format for GSTR-1
    gstr1_data = []
    total_value = 0.0
    total_gst = 0.0
    
    for hsn, data in outward_supplies.items():
        if data["transactions"]:
            entry = {
                "hsn_sac": hsn,
                "transaction_count": len(data["transactions"]),
                "total_value": round(data["total_value"], 2),
                "total_gst": round(data["total_gst"], 2),
                "transactions": data["transactions"][:10]  # Show first 10
            }
            gstr1_data.append(entry)
            total_value += data["total_value"]
            total_gst += data["total_gst"]
    
    return {
        "report_type": "GSTR-1 (Outward Supplies)",
        "filing_month": datetime.now().strftime("%m-%Y"),
        "hsn_wise_summary": gstr1_data,
        "total_outward_supply_value": round(total_value, 2),
        "total_gst_collected": round(total_gst, 2),
        "note": "This is a draft. Verify with your actual business invoices before filing."
    }


def generate_gstr3b_draft(transactions: list[Transaction]) -> dict:
    """
    GSTR-3B = Monthly return (GST collected - GST paid)
    """
    # Calculate outward supplies (GSTR-1 data)
    gst_collected = 0.0
    gst_on_sales = 0.0
    
    for txn in transactions:
        if txn.type == "credit":
            gst_rate = getattr(txn, "gst_rate", 0.0)
            gst_on_sales += (txn.amount * gst_rate) / 100
    
    gst_collected = gst_on_sales
    
    # Calculate input tax credit (GSTR-2 data - what you purchased)
    total_itc_available = 0.0
    itc_claimed = 0.0
    
    for txn in transactions:
        if txn.type == "debit":
            gst_rate = getattr(txn, "gst_rate", 0.0)
            itc_eligible = getattr(txn, "itc_eligible", False)
            gst_amount = getattr(txn, "gst_amount", None)
            if gst_amount is None:
                gst_amount = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0
            total_itc_available += gst_amount
            
            if itc_eligible:
                itc_claimed += getattr(txn, "itc_amount", gst_amount)
    
    # Net GST payable
    net_gst_payable = gst_collected - itc_claimed
    
    return {
        "report_type": "GSTR-3B (Monthly GST Return)",
        "filing_month": datetime.now().strftime("%m-%Y"),
        "section_1_outward_supplies": {
            "total_taxable_supplies": round(sum(t.amount for t in transactions if t.type == "credit"), 2),
            "gst_collected": round(gst_collected, 2)
        },
        "section_2_input_tax_credit": {
            "total_itc_available": round(total_itc_available, 2),
            "itc_claimed": round(itc_claimed, 2),
            "summary": f"Out of ₹{total_itc_available:,.2f} available ITC, you can claim ₹{itc_claimed:,.2f}"
        },
        "section_3_net_payable": {
            "gst_collected": round(gst_collected, 2),
            "itc_claimed": round(itc_claimed, 2),
            "net_gst_payable": round(max(net_gst_payable, 0), 2),
            "net_refund_available": round(max(-net_gst_payable, 0), 2)
        },
        "filing_checklist": [
            "✓ Verify all outward supplies are recorded",
            "✓ Check all ITC-eligible invoices are uploaded",
            "✓ Ensure HSN/SAC codes are correct",
            "✓ Cross-check with purchase invoices",
            "✓ Review amendments if any",
            "✓ File before deadline"
        ],
        "note": "This is a draft based on your transactions. Consult your CA before official filing."
    }


def generate_itc_summary(transactions: list[Transaction]) -> dict:
    """
    Detailed ITC (Input Tax Credit) analysis.
    """
    itc_by_category = defaultdict(lambda: {
        "eligible": 0.0,
        "ineligible": 0.0,
        "transactions": []
    })
    
    for txn in transactions:
        if txn.type == "debit":
            gst_rate = getattr(txn, "gst_rate", 0.0)
            itc_eligible = getattr(txn, "itc_eligible", False)
            category = getattr(txn, "category", "Other") or "Other"
            
            gst_amount = getattr(txn, "gst_amount", None)
            if gst_amount is None:
                gst_amount = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0
            
            if itc_eligible:
                itc_by_category[category]["eligible"] += gst_amount
            else:
                itc_by_category[category]["ineligible"] += gst_amount
            
            itc_by_category[category]["transactions"].append({
                "date": txn.date.strftime("%d-%m-%Y"),
                "party": txn.party,
                "amount": round(txn.amount, 2),
                "gst_rate": gst_rate,
                "gst_amount": round(gst_amount, 2),
                "eligible": itc_eligible
            })
    
    total_eligible = sum(v["eligible"] for v in itc_by_category.values())
    total_ineligible = sum(v["ineligible"] for v in itc_by_category.values())
    
    return {
        "report_type": "ITC Summary",
        "filing_month": datetime.now().strftime("%m-%Y"),
        "category_wise": {
            cat: {
                "eligible_itc": round(data["eligible"], 2),
                "ineligible_gst": round(data["ineligible"], 2),
                "transaction_count": len(data["transactions"]),
                "sample_transactions": data["transactions"][:3]
            }
            for cat, data in itc_by_category.items()
        },
        "totals": {
            "total_eligible_itc": round(total_eligible, 2),
            "total_ineligible_gst": round(total_ineligible, 2),
            "itc_eligibility_rate": round((total_eligible / (total_eligible + total_ineligible) * 100), 2) if (total_eligible + total_ineligible) > 0 else 0
        }
    }


def generate_gst_compliance_report(transactions: list[Transaction]) -> dict:
    """
    Complete GST compliance package.
    """
    gstr1 = generate_gstr1_draft(transactions)
    gstr3b = generate_gstr3b_draft(transactions)
    itc = generate_itc_summary(transactions)
    
    return {
        "gstr_1": gstr1,
        "gstr_3b": gstr3b,
        "itc_analysis": itc,
        "generated_at": datetime.now().isoformat(),
        "disclaimer": "These are DRAFT reports. Consult your CA/tax professional before official filing. Not a substitute for professional accounting advice."
    }
