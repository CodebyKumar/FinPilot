"""
Shared transaction model for pocket-cfo-parser.

This module will contain the data structures and classes representing
a parsed financial transaction (e.g., date, amount, vendor, category).
This shared model will be utilized by both the SMS and PDF parsing modules
to maintain a consistent data format.
"""

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal

@dataclass
class Transaction:
    # The monetary value of the transaction
    amount: float
    
    # The transaction type, either "credit" or "debit"
    type: Literal["credit", "debit"]
    
    # Merchant or person name, cleaned and title-cased
    party: str
    
    # Python datetime object representing when the transaction occurred
    date: datetime
    
    # The origin of the parsing record (e.g., sms, pdf, ocr, voice)
    source: Literal["sms", "pdf", "ocr", "voice"]
    
    # Original unparsed input, mapped for debugging purposes
    raw_text: str
    
    # Broad classification of the transaction, defaults to "uncategorized"
    category: str = "uncategorized"
    sub_category: str = "uncategorized"
    business_nature: str = "business"
    gst_rate: float = 0.0
    itc_eligible: bool = False
    hsn_sac: str = "UNKNOWN"
    gst_amount: float = 0.0
    itc_amount: float = 0.0
    matched_rule: str = "none"
    
    # A float between 0.0 and 1.0 indicating how sure the parser is about this parse
    confidence: float = 1.0

    # Auto-generated SHA256 hash of amount + date + party (for deduplication)
    id: str = field(init=False)

    def __post_init__(self):
        # Clean and title-case the party name
        if self.party:
            self.party = self.party.strip().title()
            
        # Ensure the type format is uniform
        if self.type:
            self.type = self.type.lower() # type: ignore
             
        # Generate SHA256 hash for id using amount + date (isoformat) + party
        hash_input = f"{self.amount}_{self.date.isoformat()}_{self.party}"
        self.id = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    def to_dict(self) -> dict:
        """Serializes the transaction object to a plain dictionary."""
        data = asdict(self)
        if isinstance(self.date, datetime):
            data['date'] = self.date.isoformat()
        return data

    def __str__(self) -> str:
        """Returns a readable single line representation of the transaction."""
        date_str = self.date.strftime('%Y-%m-%d')
        type_upper = self.type.upper() if self.type else "UNKNOWN"
        return f"[{type_upper}] ₹{self.amount:.2f} → {self.party} | {date_str} | {self.source}"
