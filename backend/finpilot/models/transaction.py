"""
Shared Transaction model for FinPilot.

Represents a single parsed financial transaction from any source (SMS, PDF, etc.).
Used throughout all agents and parsers as the canonical data structure.
"""

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal


@dataclass
class Transaction:
    # The monetary value of the transaction
    amount: float

    # Direction of money flow
    type: Literal["credit", "debit"]

    # Merchant or person name, cleaned and title-cased
    party: str

    # When the transaction occurred
    date: datetime

    # Origin of the record
    source: Literal["sms", "pdf", "ocr", "voice"]

    # Original unparsed input (for debugging/audit)
    raw_text: str

    # GST classification fields (populated by GST agent)
    category: str = "uncategorized"
    sub_category: str = "uncategorized"
    business_nature: str = "business"
    gst_rate: float = 0.0
    itc_eligible: bool = False
    hsn_sac: str = "UNKNOWN"
    gst_amount: float = 0.0
    itc_amount: float = 0.0
    matched_rule: str = "none"

    # Parser confidence score (0.0 – 1.0)
    confidence: float = 1.0

    # Auto-generated SHA-256 hash of (amount, date, party) for deduplication
    id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.party:
            self.party = self.party.strip().title()
        if self.type:
            self.type = self.type.lower()  # type: ignore
        hash_input = f"{self.amount}_{self.date.isoformat()}_{self.party}"
        self.id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        """Serialize to a plain dict, converting datetime to ISO string."""
        data = asdict(self)
        if isinstance(self.date, datetime):
            data["date"] = self.date.isoformat()
        return data

    def __str__(self) -> str:
        date_str = self.date.strftime("%Y-%m-%d")
        type_upper = self.type.upper() if self.type else "UNKNOWN"
        return f"[{type_upper}] ₹{self.amount:.2f} → {self.party} | {date_str} | {self.source}"
