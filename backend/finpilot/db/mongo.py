"""
MongoDB connection and operations for FinPilot.

Connection parameters are read from environment variables via finpilot.config.
No connection strings are hardcoded here.
"""

import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

from finpilot import config

logger = logging.getLogger(__name__)

# Single shared MongoClient (connection pool) for the entire application
_client: MongoClient | None = None


def _get_client() -> MongoClient:
    """Return the shared MongoClient, creating it on first access."""
    global _client
    if _client is None:
        _client = MongoClient(config.MONGODB_URI)
    return _client


def _get_db():
    return _get_client()[config.DB_NAME]


def init_db() -> None:
    """
    Perform any one-time database initialisation tasks.
    Called explicitly at application startup – not at import time.
    """
    try:
        db = _get_db()
        # Remove stale email index if it exists (legacy artefact)
        try:
            db["users"].drop_index("email_1")
        except Exception:
            pass  # Index doesn't exist – that's fine
        logger.info("Database initialised successfully.")
    except PyMongoError as exc:
        logger.error("Database initialisation failed: %s", exc)


def ping_db() -> bool:
    """Verify the MongoDB connection is alive. Returns True on success."""
    try:
        _get_client().admin.command("ping")
        logger.info("MongoDB ping: OK")
        return True
    except ConnectionFailure:
        logger.error("MongoDB ping: connection failed")
        return False
    except PyMongoError as exc:
        logger.error("MongoDB ping error: %s", exc)
        return False


def save_transaction(transaction, user_id: str):
    """
    Upsert a Transaction object into the database.
    Uses the transaction's SHA-256 hash ID to prevent duplicates.
    """
    txn_dict = transaction.to_dict()
    txn_dict["user_id"] = user_id
    txn_id = txn_dict.pop("id")

    try:
        result = _get_db()["transactions"].update_one(
            {"_id": txn_id},
            {"$set": txn_dict},
            upsert=True,
        )
        return result
    except PyMongoError as exc:
        logger.error("Failed to save transaction %s: %s", txn_id, exc)
        return None


def save_user(
    name: str, 
    phone: str, 
    business_name: str,
    industry: str = "Unknown",
    entity_type: str = "Unknown",
    annual_turnover: float = 0.0
) -> str:
    """
    Create or update a user profile keyed by phone number.
    Returns the MongoDB ObjectId as a string, or empty string on failure.
    """
    user_doc = {
        "name": name, 
        "phone": phone, 
        "business_name": business_name,
        "industry": industry,
        "entity_type": entity_type,
        "annual_turnover": annual_turnover
    }
    try:
        result = _get_db()["users"].find_one_and_update(
            {"phone": phone},
            {"$set": user_doc},
            upsert=True,
            return_document=True,
        )
        return str(result["_id"])
    except PyMongoError as exc:
        logger.error("Failed to save user %s: %s", name, exc)
        return ""


def get_user(user_id: str) -> dict | None:
    """Retrieve user profiling data."""
    try:
        from bson.objectid import ObjectId
        user = _get_db()["users"].find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
        return user
    except Exception as exc:
        logger.error("Failed to get user %s: %s", user_id, exc)
        return None


def get_transactions_by_user(user_id: str) -> list:
    """
    Retrieve all transactions for a given user, sorted newest-first.
    Returns an empty list on failure.
    """
    try:
        cursor = _get_db()["transactions"].find({"user_id": user_id}).sort("date", -1)
        return list(cursor)
    except PyMongoError as exc:
        logger.error("Failed to retrieve transactions for user %s: %s", user_id, exc)
        return []
