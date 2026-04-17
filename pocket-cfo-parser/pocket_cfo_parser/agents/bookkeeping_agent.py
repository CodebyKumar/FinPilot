"""
Bookkeeping Agent

Generates ledger-friendly bookkeeping summaries and reconciliations
from parsed transaction data.
"""

from collections import defaultdict
from datetime import datetime
from pocket_cfo_parser.models.transaction import Transaction


def build_bookkeeping_entries(transactions: list[Transaction]) -> list[dict]:
    """Create a ledger-style entry list that preserves GST/ITC details."""
    entries = []
    running_balance = 0.0

    for txn in sorted(transactions, key=lambda t: t.date):
        gst_rate = getattr(txn, "gst_rate", 0.0) or 0.0
        gst_amount = getattr(txn, "gst_amount", None)
        if gst_amount is None:
            gst_amount = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0

        itc_amount = getattr(txn, "itc_amount", 0.0) if getattr(txn, "itc_eligible", False) else 0.0

        if txn.type == "credit":
            running_balance += txn.amount
        else:
            running_balance -= txn.amount

        entries.append({
            "date": txn.date.isoformat(),
            "party": txn.party,
            "type": txn.type,
            "amount": round(txn.amount, 2),
            "category": txn.category or "Uncategorized",
            "sub_category": txn.sub_category or "Uncategorized",
            "business_nature": txn.business_nature or "business",
            "source": txn.source,
            "gst_rate": round(gst_rate, 2),
            "gst_amount": round(gst_amount, 2),
            "itc_eligible": txn.itc_eligible,
            "itc_amount": round(itc_amount, 2),
            "matched_rule": txn.matched_rule,
            "confidence": round(txn.confidence, 2),
            "raw_text": txn.raw_text,
            "running_balance": round(running_balance, 2)
        })

    return entries


def summarize_bookkeeping(transactions: list[Transaction]) -> dict:
    """Summarize cash flow and GST/ITC totals for bookkeeping review with detailed breakdowns."""
    totals = defaultdict(float)
    uncategorized = 0
    low_confidence = 0
    category_counts = defaultdict(int)
    party_counts = defaultdict(int)
    gst_rates = defaultdict(float)
    monthly_totals = defaultdict(lambda: defaultdict(float))
    business_vs_personal = defaultdict(lambda: defaultdict(float))

    for txn in transactions:
        month_key = f"{txn.date.year}-{txn.date.month:02d}"

        if txn.type == "credit":
            totals["total_credits"] += txn.amount
            monthly_totals[month_key]["credits"] += txn.amount
        else:
            totals["total_debits"] += txn.amount
            monthly_totals[month_key]["debits"] += txn.amount

        nature = getattr(txn, "business_nature", "business") or "business"
        business_vs_personal[nature][txn.type] += txn.amount

        gst_rate = getattr(txn, "gst_rate", 0.0) or 0.0
        gst_amount = getattr(txn, "gst_amount", None)
        if gst_amount is None:
            gst_amount = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0

        totals["total_gst_paid"] += gst_amount if txn.type == "debit" else 0.0
        totals["total_itc_claimable"] += getattr(txn, "itc_amount", gst_amount) if txn.type == "debit" and getattr(txn, "itc_eligible", False) else 0.0

        if gst_rate > 0:
            gst_rates[f"{gst_rate}%"] += gst_amount if txn.type == "debit" else 0.0

        if not txn.category or txn.category.lower() in {"uncategorized", "unclassified", "other"}:
            uncategorized += 1

        if txn.confidence < 0.6:
            low_confidence += 1

        category_counts[txn.category or "Uncategorized"] += 1
        party_counts[txn.party or "Unknown"] += 1

    total_credits = round(totals["total_credits"], 2)
    total_debits = round(totals["total_debits"], 2)
    total_itc_claimable = round(totals["total_itc_claimable"], 2)
    total_gst_paid = round(totals["total_gst_paid"], 2)
    net_cash_flow = round(total_credits - total_debits + total_itc_claimable, 2)

    # Calculate monthly cash flow trends
    monthly_summary = []
    for month, amounts in sorted(monthly_totals.items()):
        monthly_summary.append({
            "month": month,
            "credits": round(amounts["credits"], 2),
            "debits": round(amounts["debits"], 2),
            "net": round(amounts["credits"] - amounts["debits"], 2)
        })

    # Business vs Personal breakdown
    business_summary = {
        "business_credits": round(business_vs_personal["business"]["credit"], 2),
        "business_debits": round(business_vs_personal["business"]["debit"], 2),
        "personal_credits": round(business_vs_personal["personal"]["credit"], 2),
        "personal_debits": round(business_vs_personal["personal"]["debit"], 2)
    }

    return {
        "total_credits": total_credits,
        "total_debits": total_debits,
        "net_cash_flow": net_cash_flow,
        "total_gst_paid": total_gst_paid,
        "total_itc_claimable": total_itc_claimable,
        "transaction_count": len(transactions),
        "uncategorized_count": uncategorized,
        "low_confidence_count": low_confidence,
        "largest_parties": [{"party": party, "count": count} for party, count in sorted(party_counts.items(), key=lambda x: x[1], reverse=True)[:10]],
        "category_counts": {cat: count for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)},
        "gst_rate_breakdown": {rate: round(amount, 2) for rate, amount in sorted(gst_rates.items())},
        "monthly_trends": monthly_summary,
        "business_vs_personal": business_summary,
        "gst_efficiency": round((total_itc_claimable / total_gst_paid * 100), 2) if total_gst_paid > 0 else 0.0,
        "suggestions": [
            {
                "priority": "high",
                "message": f"{uncategorized} transactions are uncategorized. Assign proper bookkeeping categories for accurate reporting.",
                "count": uncategorized
            }
        ] if uncategorized > 0 else [],
        "action_items": [
            {
                "priority": "medium",
                "message": f"{low_confidence} transactions have low classification confidence. Verify their category and GST details.",
                "count": low_confidence
            }
        ] if low_confidence > 0 else [],
        "insights": [
            f"ITC Claim Efficiency: {round((total_itc_claimable / total_gst_paid * 100), 2) if total_gst_paid > 0 else 0.0}% of GST paid is claimable as ITC",
            f"Business Transactions: {round((business_summary['business_credits'] + business_summary['business_debits']) / (total_credits + total_debits) * 100, 2) if (total_credits + total_debits) > 0 else 0.0}% of total activity",
            f"Monthly Average: ₹{round(net_cash_flow / len(monthly_summary), 2) if monthly_summary else 0} net cash flow per month"
        ]
    }


def get_bookkeeping_summary(transactions: list[Transaction]) -> dict:
    """Return bookkeeping and cashbook-ready summaries for CA-style ledger review."""
    return {
        "entries": build_bookkeeping_entries(transactions),
        "balance_summary": summarize_bookkeeping(transactions),
        "generated_at": datetime.now().isoformat(),
        "recommendations": [
            "Export ledger entries to your accounting software for reconciliation.",
            "Verify GST and ITC details for debit transactions before filing.",
            "Separate personal and business expenses for accurate income reporting."
        ]
    }
