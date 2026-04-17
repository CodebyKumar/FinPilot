"""
MongoDB connection and operations module for pocket-cfo-parser.
"""

import os
import logging
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ConnectionFailure, PyMongoError
from dotenv import load_dotenv

# Load environment variables from the .env file in the project root
load_dotenv()

# Set up logging for robust error tracking
logger = logging.getLogger(__name__)

# Fetch connection string and DB name from the environment variables (.env)
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "pocket_cfo")

# Initialize the MongoDB client globally. 
# It's a best practice to reuse a single connection pool across the app.
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
users_collection = db['users']
transactions_collection = db['transactions']
aa_consents_collection = db['aa_consents']
aa_sessions_collection = db['aa_sessions']
vendors_collection = db['vendors']
payables_collection = db['payables']
foreign_remittances_collection = db['foreign_remittances']
gst_preflight_collection = db['gst_preflight_runs']
compliance_calendar_collection = db['compliance_calendar']
drl_requests_collection = db['drl_requests']

try:
    users_collection.drop_index("email_1")
except Exception:
    pass

def ping_db():
    """
    Tests the MongoDB connection. 
    Prints a success or failure message depending on the connection state.
    """
    try:
        # Pinging the server to verify active connection
        client.admin.command('ping')
        print("MongoDB connected")
    except ConnectionFailure:
        print("Connection failed")
    except PyMongoError as e:
        print(f"Connection failed: {e}")

def save_transaction(transaction, user_id: str):
    """
    Saves a parsed Transaction object to the database.
    Performs an upsert based on the transaction's unique custom 'id' (SHA256)
    preventing duplicate messages or reruns from appending multiple times.
    """
    # 1. Convert the Transaction dataclass into a dictionary representation
    txn_dict = transaction.to_dict()
    
    # 2. Append the required association field
    txn_dict['user_id'] = user_id
    
    # Extract the custom hash ID to map to MongoDB's innate _id 
    # to enforce absolute uniqueness and simplify indexing
    txn_id = txn_dict.pop('id')
    
    try:
        # 3. Upsert the transaction: update if the _id uniquely exists, insert if it doesn't
        result = transactions_collection.update_one(
            {'_id': txn_id},
            {'$set': txn_dict},
            upsert=True
        )
        return result
    except PyMongoError as e:
        logger.error(f"Failed to save transaction {txn_id}: {e}")
        return None

def save_user(name: str, phone: str, business_name: str) -> str:
    """
    Creates or updates a user profile document identified by phone number.
    Returns the MongoDB ObjectId as a string.
    """
    user_document = {
        "name": name,
        "phone": phone,
        "business_name": business_name
    }
    try:
        result = users_collection.find_one_and_update(
            {"phone": phone},
            {"$set": user_document},
            upsert=True,
            return_document=True
        )
        return str(result["_id"])
    except PyMongoError as e:
        logger.error(f"Failed to save user {name}: {e}")
        return ""

def get_transactions_by_user(user_id: str) -> list:
    """
    Retrieves all stored transactions exclusively associated with the user_id.
    Sorts chronologically with the newest parsed dates acting as highest priority.
    """
    try:
        # Find all documents strictly matching the user correlation 
        # Sort based on parameter 'date' defaulting to descending sorting
        cursor = transactions_collection.find({"user_id": user_id}).sort("date", -1)
        
        # Fully convert MongoDB cursor representation strictly into a Python List array
        return list(cursor)
    except PyMongoError as e:
        logger.error(f"Failed to retrieve transactions for user {user_id}: {e}")
        return []
