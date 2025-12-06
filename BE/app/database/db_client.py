from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection settings
MONGODB_URL = os.getenv(
    "MONGODB_URL", "mongodb+srv://hungnguyen2205_db_user:ASE-251-2025@ase-251.gbnjmee.mongodb.net/?appName=ASE-251")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ase")

# Global client instance
client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo():
    """Connect to MongoDB."""
    global client
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        # Test the connection
        await client.admin.command('ping')
        print(
            f"✅ Successfully connected to MongoDB! Database: {DATABASE_NAME}")
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("🔌 MongoDB connection closed")


def get_database():
    """Get database instance."""
    if client is None:
        raise Exception(
            "Database not connected. Call connect_to_mongo() first.")
    return client[DATABASE_NAME]


def get_users_collection():
    """Get users collection."""
    db = get_database()
    return db["users"]


def get_refresh_tokens_collection():
    """Get refresh_tokens collection."""
    db = get_database()
    return db["refresh_tokens"]


def get_bookings_collection():
    """Get bookings collection."""
    db = get_database()
    return db["bookings"]
