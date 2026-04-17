"""
GST Agent

Determines GST classifications and calculates Input Tax Credit (ITC) eligibility
via a deterministic rules engine, with an OpenAI LLM fallback for unknown vendors.

AI model and API key are read from environment variables (finpilot.config).
"""

import json
import logging

from finpilot import config
from finpilot.models.transaction import Transaction

logger = logging.getLogger(__name__)

# ─── Rules engine ─────────────────────────────────────────────────────────────

GST_RULES: dict[str, dict] = {
    "blinkit":         {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Grocery"},
    "zepto":           {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Grocery"},
    "bigbasket":       {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Grocery"},
    "grofers":         {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Grocery"},
    "dmart":           {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Grocery"},
    "reliance fresh":  {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Grocery"},
    "more supermarket":{"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Grocery"},
    "spencers":        {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Grocery"},
    "apollo":          {"gst_rate": 12.0, "hsn_sac": "9993", "itc_eligible": False, "category": "Pharma & Health"},
    "netmeds":         {"gst_rate": 12.0, "hsn_sac": "9993", "itc_eligible": False, "category": "Pharma & Health"},
    "pharmeasy":       {"gst_rate": 12.0, "hsn_sac": "9993", "itc_eligible": False, "category": "Pharma & Health"},
    "medplus":         {"gst_rate": 12.0, "hsn_sac": "9993", "itc_eligible": False, "category": "Pharma & Health"},
    "1mg":             {"gst_rate": 12.0, "hsn_sac": "9993", "itc_eligible": False, "category": "Pharma & Health"},
    "thyrocare":       {"gst_rate": 12.0, "hsn_sac": "9993", "itc_eligible": False, "category": "Pharma & Health"},
    "lenskart":        {"gst_rate": 12.0, "hsn_sac": "9993", "itc_eligible": False, "category": "Pharma & Health"},
    "rapido":          {"gst_rate": 5.0,  "hsn_sac": "9964", "itc_eligible": False, "category": "Ride & Logistics"},
    "dunzo":           {"gst_rate": 18.0, "hsn_sac": "9967", "itc_eligible": True,  "category": "Ride & Logistics"},
    "porter":          {"gst_rate": 18.0, "hsn_sac": "9967", "itc_eligible": True,  "category": "Ride & Logistics"},
    "delhivery":       {"gst_rate": 18.0, "hsn_sac": "9967", "itc_eligible": True,  "category": "Ride & Logistics"},
    "bluedart":        {"gst_rate": 18.0, "hsn_sac": "9967", "itc_eligible": True,  "category": "Ride & Logistics"},
    "dtdc":            {"gst_rate": 18.0, "hsn_sac": "9967", "itc_eligible": True,  "category": "Ride & Logistics"},
    "ecom express":    {"gst_rate": 18.0, "hsn_sac": "9967", "itc_eligible": True,  "category": "Ride & Logistics"},
    "myntra":          {"gst_rate": 12.0, "hsn_sac": "9961", "itc_eligible": True,  "category": "Fashion & Lifestyle"},
    "nykaa":           {"gst_rate": 12.0, "hsn_sac": "9961", "itc_eligible": True,  "category": "Fashion & Lifestyle"},
    "ajio":            {"gst_rate": 12.0, "hsn_sac": "9961", "itc_eligible": True,  "category": "Fashion & Lifestyle"},
    "meesho":          {"gst_rate": 12.0, "hsn_sac": "9961", "itc_eligible": True,  "category": "Fashion & Lifestyle"},
    "bewakoof":        {"gst_rate": 12.0, "hsn_sac": "9961", "itc_eligible": True,  "category": "Fashion & Lifestyle"},
    "paytm":           {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": True,  "category": "Payments & Fintech"},
    "phonepe":         {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": True,  "category": "Payments & Fintech"},
    "gpay":            {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": True,  "category": "Payments & Fintech"},
    "razorpay":        {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": True,  "category": "Payments & Fintech"},
    "cashfree":        {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": True,  "category": "Payments & Fintech"},
    "mcdonald":        {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food Chains"},
    "dominos":         {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food Chains"},
    "pizza hut":       {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food Chains"},
    "kfc":             {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food Chains"},
    "subway":          {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food Chains"},
    "starbucks":       {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food Chains"},
    "cafe coffee day": {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food Chains"},
    "google":          {"gst_rate": 18.0, "hsn_sac": "9984", "itc_eligible": True,  "category": "Telecom & Cloud"},
    "microsoft":       {"gst_rate": 18.0, "hsn_sac": "9984", "itc_eligible": True,  "category": "Telecom & Cloud"},
    "aws":             {"gst_rate": 18.0, "hsn_sac": "9984", "itc_eligible": True,  "category": "Telecom & Cloud"},
    "digitalocean":    {"gst_rate": 18.0, "hsn_sac": "9984", "itc_eligible": True,  "category": "Telecom & Cloud"},
    "godaddy":         {"gst_rate": 18.0, "hsn_sac": "9984", "itc_eligible": True,  "category": "Telecom & Cloud"},
    "udemy":           {"gst_rate": 18.0, "hsn_sac": "9992", "itc_eligible": False, "category": "Education"},
    "coursera":        {"gst_rate": 18.0, "hsn_sac": "9992", "itc_eligible": False, "category": "Education"},
    "unacademy":       {"gst_rate": 18.0, "hsn_sac": "9992", "itc_eligible": False, "category": "Education"},
    "byju":            {"gst_rate": 18.0, "hsn_sac": "9992", "itc_eligible": False, "category": "Education"},
    "vedantu":         {"gst_rate": 18.0, "hsn_sac": "9992", "itc_eligible": False, "category": "Education"},
    "hpcl":            {"gst_rate": 0.0,  "hsn_sac": "EXEMPT", "itc_eligible": False, "category": "Fuel"},
    "bpcl":            {"gst_rate": 0.0,  "hsn_sac": "EXEMPT", "itc_eligible": False, "category": "Fuel"},
    "iocl":            {"gst_rate": 0.0,  "hsn_sac": "EXEMPT", "itc_eligible": False, "category": "Fuel"},
    "petrol":          {"gst_rate": 0.0,  "hsn_sac": "EXEMPT", "itc_eligible": False, "category": "Fuel"},
    "diesel":          {"gst_rate": 0.0,  "hsn_sac": "EXEMPT", "itc_eligible": False, "category": "Fuel"},
    "processing fee":  {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": True,  "category": "Banking Fees"},
    "bank charges":    {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": True,  "category": "Banking Fees"},
    "emi":             {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": True,  "category": "Banking Fees"},
    "swiggy":          {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Beverage"},
    "zomato":          {"gst_rate": 5.0,  "hsn_sac": "9963", "itc_eligible": False, "category": "Food & Beverage"},
    "amazon":          {"gst_rate": 18.0, "hsn_sac": "9961", "itc_eligible": True,  "category": "Retail & E-commerce"},
    "flipkart":        {"gst_rate": 18.0, "hsn_sac": "9961", "itc_eligible": True,  "category": "Retail & E-commerce"},
    "uber":            {"gst_rate": 5.0,  "hsn_sac": "9964", "itc_eligible": False, "category": "Transport"},
    "ola":             {"gst_rate": 5.0,  "hsn_sac": "9964", "itc_eligible": False, "category": "Transport"},
    "airtel":          {"gst_rate": 18.0, "hsn_sac": "9984", "itc_eligible": True,  "category": "Telecommunications"},
    "jio":             {"gst_rate": 18.0, "hsn_sac": "9984", "itc_eligible": True,  "category": "Telecommunications"},
    "electricity":     {"gst_rate": 0.0,  "hsn_sac": "EXEMPT", "itc_eligible": False, "category": "Utilities"},
    "rent":            {"gst_rate": 18.0, "hsn_sac": "9972", "itc_eligible": True,  "category": "Rent & Real Estate"},
    "salary":          {"gst_rate": 0.0,  "hsn_sac": "EXEMPT", "itc_eligible": False, "category": "Payroll"},
    "medical":         {"gst_rate": 0.0,  "hsn_sac": "9993", "itc_eligible": False, "category": "Healthcare"},
    "hotel":           {"gst_rate": 12.0, "hsn_sac": "9963", "itc_eligible": True,  "category": "Accommodation"},
    "airline":         {"gst_rate": 5.0,  "hsn_sac": "9964", "itc_eligible": True,  "category": "Airlines"},
    "railway":         {"gst_rate": 5.0,  "hsn_sac": "9964", "itc_eligible": True,  "category": "Railways"},
    "insurance":       {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": True,  "category": "Financial Services"},
    "mutual fund":     {"gst_rate": 18.0, "hsn_sac": "9971", "itc_eligible": False, "category": "Investments"},
    "netflix":         {"gst_rate": 18.0, "hsn_sac": "9984", "itc_eligible": False, "category": "Software & Subscriptions"},
    "software":        {"gst_rate": 18.0, "hsn_sac": "9973", "itc_eligible": True,  "category": "Software & Subscriptions"},
    "office supplies": {"gst_rate": 18.0, "hsn_sac": "9983", "itc_eligible": True,  "category": "Office Expenses"},
}

CATEGORY_METADATA: dict[str, dict] = {
    "Food & Grocery":          {"business_nature": "personal", "sub_category": "Groceries"},
    "Pharma & Health":         {"business_nature": "personal", "sub_category": "Medical Supplies"},
    "Ride & Logistics":        {"business_nature": "business", "sub_category": "Delivery & Logistics"},
    "Fashion & Lifestyle":     {"business_nature": "business", "sub_category": "Apparel"},
    "Payments & Fintech":      {"business_nature": "business", "sub_category": "Payment Services"},
    "Food Chains":             {"business_nature": "personal", "sub_category": "Dining Out"},
    "Telecom & Cloud":         {"business_nature": "business", "sub_category": "Telecom & Internet"},
    "Education":               {"business_nature": "personal", "sub_category": "Education"},
    "Fuel":                    {"business_nature": "personal", "sub_category": "Fuel"},
    "Banking Fees":            {"business_nature": "business", "sub_category": "Bank Charges"},
    "Retail & E-commerce":     {"business_nature": "business", "sub_category": "E-commerce"},
    "Transport":               {"business_nature": "personal", "sub_category": "Transport"},
    "Utilities":               {"business_nature": "business", "sub_category": "Utilities"},
    "Rent & Real Estate":      {"business_nature": "business", "sub_category": "Rent"},
    "Payroll":                 {"business_nature": "business", "sub_category": "Payroll"},
    "Healthcare":              {"business_nature": "personal", "sub_category": "Healthcare"},
    "Accommodation":           {"business_nature": "business", "sub_category": "Travel Accommodation"},
    "Airlines":                {"business_nature": "business", "sub_category": "Business Travel"},
    "Railways":                {"business_nature": "business", "sub_category": "Travel"},
    "Financial Services":      {"business_nature": "business", "sub_category": "Financial Services"},
    "Investments":             {"business_nature": "personal", "sub_category": "Investments"},
    "Software & Subscriptions":{"business_nature": "business", "sub_category": "Software"},
    "Office Expenses":         {"business_nature": "business", "sub_category": "Office Supplies"},
    "Food & Beverage":         {"business_nature": "personal", "sub_category": "Food & Beverage"},
    "Telecommunications":      {"business_nature": "business", "sub_category": "Telecom"},
    "Uncategorized":           {"business_nature": "business", "sub_category": "Uncategorized"},
}

_FALLBACK_PAYLOAD: dict = {
    "hsn_sac": "UNKNOWN",
    "gst_rate": 18.0,
    "itc_eligible": False,
    "category": "Uncategorized",
    "sub_category": "Uncategorized",
    "business_nature": "business",
    "matched_rule": "none",
    "confidence": 0.4,
}


def _get_category_metadata(category: str) -> dict:
    return CATEGORY_METADATA.get(category, {"business_nature": "business", "sub_category": "General"})


# ─── AI fallback ──────────────────────────────────────────────────────────────

def _classify_with_openai(party: str, amount: float) -> dict:
    """
    Use OpenAI to classify a transaction when the rules engine has no match.
    Model and API key are sourced from finpilot.config (environment variables).
    Returns the fallback payload if the key is missing or the call fails.
    """
    if not config.OPENAI_API_KEY or not party or party.lower() == "unknown":
        return _FALLBACK_PAYLOAD.copy()

    try:
        from openai import OpenAI  # imported lazily – optional dependency
        client = OpenAI(api_key=config.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a GST classification engine for Indian businesses. Respond in JSON only.",
                },
                {
                    "role": "user",
                    "content": (
                        f'Classify the merchant "{party}" (amount: Rs.{amount}) into one of these categories:\n'
                        "Food & Beverage, Food & Grocery, Transport, Utilities, Healthcare, Retail & E-commerce,\n"
                        "Software & Subscriptions, Financial Services, Education, Fuel, Payroll,\n"
                        "Telecom & Cloud, Ride & Logistics, Fashion & Lifestyle, Payments & Fintech,\n"
                        "Banking Fees, Accommodation, Pharma & Health, Uncategorized.\n\n"
                        "Return JSON with exactly these fields:\n"
                        "- category: string\n"
                        "- sub_category: string\n"
                        "- business_nature: string (business or personal)\n"
                        "- gst_rate: float (one of 0, 5, 12, 18, 28)\n"
                        "- itc_eligible: boolean\n"
                        "- hsn_sac: string (e.g. '9984' or 'EXEMPT')"
                    ),
                },
            ],
        )

        result = json.loads(response.choices[0].message.content)
        return {
            "hsn_sac":        result.get("hsn_sac", "UNKNOWN"),
            "gst_rate":       float(result.get("gst_rate", 18.0)),
            "itc_eligible":   bool(result.get("itc_eligible", False)),
            "category":       result.get("category", "Uncategorized"),
            "sub_category":   result.get("sub_category", "Uncategorized"),
            "business_nature":result.get("business_nature", "business"),
            "matched_rule":   "openai",
            "confidence":     0.75,
        }
    except Exception as exc:
        logger.error("OpenAI classification failed: %s", exc)
        return _FALLBACK_PAYLOAD.copy()


# ─── Public API ───────────────────────────────────────────────────────────────

def classify_transaction(transaction: Transaction) -> dict:
    """
    Classify a transaction and return its GST parameters.
    First tries the deterministic rules engine; falls back to OpenAI LLM.
    """
    party_lower = transaction.party.lower() if transaction.party else ""

    for key, rule in GST_RULES.items():
        if key in party_lower:
            gst_rate    = rule["gst_rate"]
            itc_eligible = rule["itc_eligible"]
            gst_amount  = transaction.amount * gst_rate / (100.0 + gst_rate)
            itc_amount  = gst_amount if itc_eligible else 0.0
            category    = rule["category"]
            metadata    = _get_category_metadata(category)
            return {
                "hsn_sac":        rule["hsn_sac"],
                "gst_rate":       gst_rate,
                "itc_eligible":   itc_eligible,
                "category":       category,
                "sub_category":   metadata["sub_category"],
                "business_nature":metadata["business_nature"],
                "gst_amount":     round(gst_amount, 2),
                "itc_amount":     round(itc_amount, 2),
                "matched_rule":   key,
                "confidence":     0.9,
            }

    # LLM fallback
    ai_result = _classify_with_openai(transaction.party, transaction.amount)
    gst_rate    = ai_result["gst_rate"]
    itc_eligible = ai_result["itc_eligible"]
    gst_amount  = transaction.amount * gst_rate / (100.0 + gst_rate)
    itc_amount  = gst_amount if itc_eligible else 0.0
    ai_result["gst_amount"] = round(gst_amount, 2)
    ai_result["itc_amount"] = round(itc_amount, 2)
    ai_result.setdefault("sub_category",    "Uncategorized")
    ai_result.setdefault("business_nature", "business")
    return ai_result


def analyze_itc_opportunities(transactions: list[Transaction]) -> dict:
    """
    Scan a list of transactions and aggregate all claimable Input Tax Credit.
    """
    total_itc = 0.0
    itc_transactions: list[dict] = []
    missed_itc_count = 0

    for txn in transactions:
        if txn.type != "debit":
            continue
        classification = classify_transaction(txn)
        if classification["confidence"] <= 0.4 and classification["category"] == "Uncategorized":
            missed_itc_count += 1
        if classification["itc_amount"] > 0:
            total_itc += classification["itc_amount"]
            decorated = txn.to_dict()
            decorated["gst_classification"] = classification
            itc_transactions.append(decorated)

    total_itc = round(total_itc, 2)
    return {
        "total_itc_claimable": total_itc,
        "itc_transactions":    itc_transactions,
        "missed_itc_count":    missed_itc_count,
        "summary": f"You can claim ₹{total_itc:,.2f} in Input Tax Credit across {len(itc_transactions)} transactions.",
    }
