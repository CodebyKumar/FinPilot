"""
API-based Data Seeding Script

Posts realistic bank SMS messages to the live FastAPI backend
so all agents process and store them correctly.
"""

import sys
import time
import requests
from datetime import datetime

from finpilot import config
from finpilot.models.transaction import Transaction
from finpilot.db.mongo import save_transaction
from finpilot.agents.gst_agent import classify_transaction

API_BASE = config.API_BASE


def create_user() -> str:
    payload = {
        "name": "Demo Business",
        "phone": "9876543210",
        "business_name": "Sharma General Traders",
        "industry": "Retail",
        "entity_type": "Sole Proprietorship",
        "annual_turnover": 4500000.0
    }
    resp = requests.post(f"{API_BASE}/users/create", json=payload)
    data = resp.json()
    uid = data.get("backend_user_id", "")
    print(f"\n[+] User created via User Profiler API -> {uid}\n")
    return uid


def seed_transactions(user_id: str):
    # For standalone execution, we provide raw dummy entries representing a parsed state
    sample_txns = [
        Transaction(amount=50000.0, type="credit", party="Sharma Traders", date=datetime.now(), source="manual", raw_text="credit 50k", confidence=0.9),
        Transaction(amount=25000.0, type="debit", party="Your A/C Xxxxxxxx1234", date=datetime.now(), source="manual", raw_text="debit 25k withdraw", confidence=0.9),
        Transaction(amount=400.0, type="debit", party="Zomato", date=datetime.now(), source="manual", raw_text="zomato lunch", confidence=0.9),
        Transaction(amount=10000.0, type="credit", party="Sharmaji", date=datetime.now(), source="manual", raw_text="credit from sharmaji", confidence=0.9)
    ]

    print(f"[*] Seeding {len(sample_txns)} Transactions directly to DB...\n")

    for i, txn in enumerate(sample_txns, 1):
        try:
            # Classification runs before save
            classification = classify_transaction(txn)
            txn.category = classification.get("category", "Uncategorized")
            txn.itc_eligible = classification.get("itc_eligible", False)
            txn.confidence = max(txn.confidence, classification.get("confidence", 0.0))
            
            save_transaction(txn, user_id)
            symbol   = "+" if txn.type == "credit" else "-"
            print(f"  [{i:02d}] OK    {txn.type.upper():<6} {symbol}Rs.{txn.amount:>10,.2f}  | {txn.party:<28} | {txn.category:<30}")
        except Exception as e:
            print(f"  [{i:02d}] ERR   {e}")
        time.sleep(0.1)

    print(f"\n{'-'*80}")
    print(f"  OK: {len(sample_txns)} Seeded")
    print(f"{'-'*80}")


def print_summary(user_id: str):
    print("\n[*] Running agent summary...\n")
    try:
        actions_resp = requests.get(f"{API_BASE}/actions/{user_id}").json()
        cards = actions_resp.get("actions", [])
        
        red   = [a for a in cards if a.get("priority") == "red"]
        amber = [a for a in cards if a.get("priority") == "amber"]
        green = [a for a in cards if a.get("priority") == "green"]

        print(f"  [RED]   Critical    : {len(red)}")
        print(f"  [AMBER] Warnings    : {len(amber)}")
        print(f"  [GREEN] Opportunity : {len(green)}")
        
        for a in cards:
            tag = {"red": "[RED]", "amber": "[AMB]", "green": "[GRN]"}.get(a.get("priority"), "[?]")
            amt = f"  Rs.{a['amount']:,.2f}" if a.get("amount") is not None else ""
            print(f"\n  {tag} {a.get('title')}{amt}")
            print(f"       {a.get('message')}")
    except Exception as e:
        print(f"  [-] Could not fetch actions: {e}")


def main():
    print("=" * 80)
    print("       FINPILOT AI -- AGENT TEST DATA SEEDER")
    print("=" * 80)

    try:
        requests.get(f"{API_BASE}/health", timeout=3)
    except Exception:
        print("\n[-] Backend is not running. Start it first:\n")
        print("   cd backend && uv run serve\n")
        sys.exit(1)

    user_id = create_user()
    if not user_id:
        print("[-] Failed to create user. Check if MongoDB is connected.")
        sys.exit(1)

    seed_transactions(user_id)
    print_summary(user_id)

    print(f"\n{'='*80}")
    print(f"  DONE -- paste this User ID into the testing dashboard:")
    print(f"\n      {user_id}\n")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
