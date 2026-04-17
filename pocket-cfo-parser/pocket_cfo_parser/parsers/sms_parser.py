"""
SMS parsing module.

This module will be responsible for taking raw SMS strings (e.g., bank alerts,
credit card swipe notifications) and extracting relevant financial information.
It will utilize regular expressions or other text parsing techniques to identify
amounts, dates, and vendors, and return Transaction objects.
"""

import re
from datetime import datetime
from dateutil import parser as date_parser
from pocket_cfo_parser.models.transaction import Transaction

def parse_sms(text: str) -> Transaction | None:
    """
    Parses a raw bank SMS string into a Transaction object.
    Returns None if the SMS is a non-transaction message (OTP, promotion, failure).
    """
    text_lower = text.lower()
    
    # 1. Filter out non-transaction messages
    # Messages containing words like "OTP", "offer", etc. are skipped
    ignore_keywords = ["otp", "offer", "apply", "click", "login", "declined", "failed"]
    if any(keyword in text_lower for keyword in ignore_keywords):
        return None

    # 2. Detect if the transaction is a credit or debit based on keywords
    credit_keywords = ["credited", "deposited", "received"]
    debit_keywords = ["debited", "withdrawn", "sent"]
    
    txn_type = None
    if any(keyword in text_lower for keyword in credit_keywords):
        txn_type = "credit"
    elif any(keyword in text_lower for keyword in debit_keywords):
        txn_type = "debit"
    else:
        # If we can't find a matching keyword, safely return None
        return None

    # 3. Extract the amount
    # Matches common Indian money formats like Rs. 1,250.50, Rs1250.50, INR 3,400.00, Rs 5,000.00
    amount_match = re.search(r"(?:rs\.?|inr)\s*([\d,]+\.?\d*)", text_lower)
    if not amount_match:
        return None
    
    # Strip commas and convert to a float
    amount_str = amount_match.group(1).replace(",", "")
    try:
        amount = float(amount_str)
    except ValueError:
        return None

    # 4. Extract the party name
    party = ""
    
    # Common regex patterns to look for the recipient or sender in bank SMS 
    patterns = [
        r"trf to\s+(.*?)(?:\s+ref|\.|\s+upi)",
        r"info:\s*upi-(.*?)-",
        r"info:\s*upi/[^/]+/([^/]+)/",
        r"\(by:\s*(.*?)\)",
        r"(?:sent\s+)?to\s+(?:vpa\s+)?(.*?)(?:\.|\s+ref|\s+via|\s+upi|\son\s)",
        r"from\s+(.*?)(?:\.|\s+ref|\s+on\s)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
             raw_party = match.group(1).strip()
             
             # Strip out UPI handles like @icici or @ybl
             raw_party = re.sub(r'@[a-zA-Z0-9]+', '', raw_party).strip()
             
             # Avoid mapping 'UPI' as the actual party
             if raw_party.lower() != 'upi' and len(raw_party) > 1:
                 party = raw_party
                 break

    # 5. Extract the date
    # Handles variations like 14-Apr-26, 14-04-2026, 13Apr26
    txn_date = None
    date_match = re.search(r"(\d{2}[- /]?[A-Za-z]{3}[- /]?\d{2,4}|\d{2}[- /]?\d{2}[- /]?\d{2,4})", text)
    if date_match:
        try:
            # Use dayfirst=True since Indian banks often use DD-MM-YYYY format
            txn_date = date_parser.parse(date_match.group(1), dayfirst=True)
        except Exception:
            pass
            
    if not txn_date:
        # Fallback if no date could be parsed
        txn_date = datetime.now()

    # 6. Set confidence score based on the extraction
    confidence = 0.9
    if not party:
        party = "Unknown"
        # Reduce confidence if we wasn't able to extract party cleanly
        confidence = 0.6

    # 7. Generate and return the fully populated Transaction object
    # (Note: id hash generation is handled natively via Transaction class __post_init__)
    return Transaction(
        amount=amount,
        type=txn_type, # type: ignore
        party=party,
        date=txn_date,
        source="sms",
        raw_text=text,
        confidence=confidence
    )
