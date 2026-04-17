"""
Bookkeeping Agent

Generates ledger-style bookkeeping summaries and cash flow overviews
from parsed transaction data, ready for CA-style review.
"""

from collections import defaultdict
from datetime import datetime

from finpilot.models.transaction import Transaction


def build_bookkeeping_entries(transactions: list[Transaction]) -> list[dict]:
    """Create a chronological ledger entry list with full GST/ITC details."""
    entries     = []
    running_bal = 0.0

    for txn in sorted(transactions, key=lambda t: t.date):
        gst_rate   = getattr(txn, "gst_rate", 0.0) or 0.0
        gst_amount = getattr(txn, "gst_amount", None)
        if gst_amount is None:
            gst_amount = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0
        itc_amount = (
            getattr(txn, "itc_amount", 0.0)
            if getattr(txn, "itc_eligible", False) else 0.0
        )

        if txn.type == "credit":
            running_bal += txn.amount
        else:
            running_bal -= txn.amount

        entries.append({
            "date":            txn.date.isoformat(),
            "party":           txn.party,
            "type":            txn.type,
            "amount":          round(txn.amount, 2),
            "category":        txn.category or "Uncategorized",
            "sub_category":    txn.sub_category or "Uncategorized",
            "business_nature": txn.business_nature or "business",
            "source":          txn.source,
            "gst_rate":        round(gst_rate, 2),
            "gst_amount":      round(gst_amount, 2),
            "itc_eligible":    txn.itc_eligible,
            "itc_amount":      round(itc_amount, 2),
            "matched_rule":    txn.matched_rule,
            "confidence":      round(txn.confidence, 2),
            "raw_text":        txn.raw_text,
            "running_balance": round(running_bal, 2),
        })

    return entries


def summarize_bookkeeping(transactions: list[Transaction]) -> dict:
    """Summarize cash flow, GST/ITC totals, and generate actionable insights."""
    totals: dict[str, float]  = defaultdict(float)
    category_counts: dict     = defaultdict(int)
    party_counts: dict        = defaultdict(int)
    gst_rates: dict           = defaultdict(float)
    monthly_totals: dict      = defaultdict(lambda: defaultdict(float))
    business_vs_personal: dict= defaultdict(lambda: defaultdict(float))
    uncategorized = low_confidence = 0

    for txn in transactions:
        month_key = f"{txn.date.year}-{txn.date.month:02d}"

        if txn.type == "credit":
            totals["total_credits"]      += txn.amount
            monthly_totals[month_key]["credits"] += txn.amount
        else:
            totals["total_debits"]       += txn.amount
            monthly_totals[month_key]["debits"]  += txn.amount

        nature = getattr(txn, "business_nature", "business") or "business"
        business_vs_personal[nature][txn.type] += txn.amount

        gst_rate   = getattr(txn, "gst_rate", 0.0) or 0.0
        gst_amount = getattr(txn, "gst_amount", None)
        if gst_amount is None:
            gst_amount = (txn.amount * gst_rate) / (100 + gst_rate) if gst_rate > 0 else 0.0

        if txn.type == "debit":
            totals["total_gst_paid"] += gst_amount
            if getattr(txn, "itc_eligible", False):
                totals["total_itc_claimable"] += getattr(txn, "itc_amount", gst_amount)

        if gst_rate > 0:
            gst_rates[f"{gst_rate}%"] += gst_amount if txn.type == "debit" else 0.0

        if not txn.category or txn.category.lower() in {"uncategorized", "unclassified", "other"}:
            uncategorized += 1
        if txn.confidence < 0.6:
            low_confidence += 1

        category_counts[txn.category or "Uncategorized"] += 1
        party_counts[txn.party or "Unknown"]             += 1

    total_credits    = round(totals["total_credits"], 2)
    total_debits     = round(totals["total_debits"], 2)
    total_itc        = round(totals["total_itc_claimable"], 2)
    total_gst        = round(totals["total_gst_paid"], 2)
    net_cash_flow    = round(total_credits - total_debits + total_itc, 2)

    monthly_summary = [
        {
            "month":   month,
            "credits": round(amounts["credits"], 2),
            "debits":  round(amounts["debits"],  2),
            "net":     round(amounts["credits"] - amounts["debits"], 2),
        }
        for month, amounts in sorted(monthly_totals.items())
    ]

    business_summary = {
        "business_credits": round(business_vs_personal["business"]["credit"], 2),
        "business_debits":  round(business_vs_personal["business"]["debit"],  2),
        "personal_credits": round(business_vs_personal["personal"]["credit"], 2),
        "personal_debits":  round(business_vs_personal["personal"]["debit"],  2),
    }

    total_activity   = total_credits + total_debits
    itc_efficiency   = round(total_itc / total_gst * 100, 2) if total_gst > 0 else 0.0
    biz_pct          = round(
        (business_summary["business_credits"] + business_summary["business_debits"]) /
        total_activity * 100, 2
    ) if total_activity > 0 else 0.0
    monthly_avg_net  = round(net_cash_flow / len(monthly_summary), 2) if monthly_summary else 0.0

    return {
        "total_credits":         total_credits,
        "total_debits":          total_debits,
        "net_cash_flow":         net_cash_flow,
        "total_gst_paid":        total_gst,
        "total_itc_claimable":   total_itc,
        "transaction_count":     len(transactions),
        "uncategorized_count":   uncategorized,
        "low_confidence_count":  low_confidence,
        "largest_parties": [
            {"party": p, "count": c}
            for p, c in sorted(party_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ],
        "category_counts": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)),
        "gst_rate_breakdown": {r: round(a, 2) for r, a in sorted(gst_rates.items())},
        "monthly_trends":        monthly_summary,
        "business_vs_personal":  business_summary,
        "gst_efficiency":        itc_efficiency,
        "suggestions": [{
            "priority": "high",
            "message": (
                f"{uncategorized} transactions are uncategorized. "
                "Assign proper bookkeeping categories for accurate reporting."
            ),
            "count": uncategorized,
        }] if uncategorized > 0 else [],
        "action_items": [{
            "priority": "medium",
            "message": (
                f"{low_confidence} transactions have low classification confidence. "
                "Verify their category and GST details."
            ),
            "count": low_confidence,
        }] if low_confidence > 0 else [],
        "insights": [
            f"ITC Claim Efficiency: {itc_efficiency}% of GST paid is claimable as ITC",
            f"Business Transactions: {biz_pct}% of total activity",
            f"Monthly Average: ₹{monthly_avg_net} net cash flow per month",
        ],
    }


def get_bookkeeping_summary(transactions: list[Transaction]) -> dict:
    """Return a complete bookkeeping summary for CA-style ledger review."""
    return {
        "entries":         build_bookkeeping_entries(transactions),
        "balance_summary": summarize_bookkeeping(transactions),
        "generated_at":    datetime.now().isoformat(),
        "recommendations": [
            "Export ledger entries to your accounting software for reconciliation.",
            "Verify GST and ITC details for debit transactions before filing.",
            "Separate personal and business expenses for accurate income reporting.",
        ],
    }
