"""
API-based Data Seeding Script
Posts 60 realistic bank SMS messages to the live FastAPI backend
so all agents (GST, Expense, Profit) process and store them correctly.
"""

import sys
import time
import requests

API_BASE = "http://localhost:8000"


def create_user() -> str:
    payload = {
        "name": "Demo Business",
        "phone": "9876543210",
        "business_name": "Sharma General Traders"
    }
    resp = requests.post(f"{API_BASE}/users/create", json=payload)
    data = resp.json()
    uid = data.get("backend_user_id", "")
    print(f"\n[+] User created -> {uid}\n")
    return uid


def seed_sms(user_id: str):
    sys.path.insert(0, ".")
    from tests.test_data.sample_sms import SAMPLE_SMS

    print(f"[*] Seeding {len(SAMPLE_SMS)} SMS messages...\n")
    ok = skip = fail = 0

    for i, sms in enumerate(SAMPLE_SMS, 1):
        try:
            resp = requests.post(
                f"{API_BASE}/ingest/sms",
                json={"user_id": user_id, "text": sms},
                timeout=15
            )
            data = resp.json()
            if data.get("status") == "skipped":
                skip += 1
                print(f"  [{i:02d}] SKIP  (non-transactional)")
            elif data.get("amount") is not None:
                ok += 1
                txn_type = data.get("type", "?").upper()
                party    = data.get("party", "Unknown")
                amount   = data.get("amount", 0)
                cat      = data.get("category", "Uncategorized")
                conf     = int((data.get("confidence", 0)) * 100)
                symbol   = "+" if txn_type == "CREDIT" else "-"
                print(f"  [{i:02d}] OK    {txn_type:<6} {symbol}Rs.{amount:>10,.2f}  | {party:<28} | {cat:<30} | {conf}%")
            else:
                fail += 1
                print(f"  [{i:02d}] FAIL  Unexpected: {data}")
        except Exception as e:
            fail += 1
            print(f"  [{i:02d}] ERR   {e}")

        time.sleep(0.1)

    print(f"\n{'-'*80}")
    print(f"  OK: {ok}   Skipped: {skip}   Failed: {fail}")
    print(f"{'-'*80}")


def print_summary(user_id: str):
    print("\n[*] Running agent summary...\n")
    try:
        actions = requests.get(f"{API_BASE}/actions/{user_id}").json()
        cards   = actions.get("actions", [])
        red     = [a for a in cards if a["priority"] == "red"]
        amber   = [a for a in cards if a["priority"] == "amber"]
        green   = [a for a in cards if a["priority"] == "green"]

        print(f"  [RED]   Critical    : {len(red)}")
        print(f"  [AMBER] Warnings    : {len(amber)}")
        print(f"  [GREEN] Opportunity : {len(green)}")
        for a in cards:
            tag = {"red": "[RED]", "amber": "[AMB]", "green": "[GRN]"}.get(a["priority"], "[?]")
            amt = f"  Rs.{a['amount']:,.2f}" if a.get("amount") is not None else ""
            print(f"\n  {tag} {a['title']}{amt}")
            print(f"       {a['message']}")
    except Exception as e:
        print(f"  [-] Could not fetch actions: {e}")


def main():
    print("=" * 80)
    print("       POCKET CFO -- AGENT TEST DATA SEEDER")
    print("=" * 80)

    try:
        requests.get(f"{API_BASE}/health", timeout=3)
    except Exception:
        print("\n[-] Backend is not running. Start it first:\n")
        print("   cd pocket-cfo-parser && source .venv/Scripts/activate && uvicorn api.main:app --reload --port 8000\n")
        sys.exit(1)

    user_id = create_user()
    if not user_id:
        print("[-] Failed to create user. Check if MongoDB is connected.")
        sys.exit(1)

    seed_sms(user_id)
    print_summary(user_id)

    print(f"\n{'='*80}")
    print(f"  DONE -- paste this User ID into the testing dashboard:")
    print(f"\n      {user_id}\n")
    print(f"  Dashboard -> http://localhost:5500")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
