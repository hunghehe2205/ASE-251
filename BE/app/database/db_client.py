from pymongo import AsyncMongoClient
from pymongo.server_api import ServerApi
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import MONGODB_URI, DATABASE_NAME

# Global async client instance
client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo():
    """Connect to MongoDB using async client."""
    global client
    try:
        client = AsyncIOMotorClient(MONGODB_URI)
        # Test the connection
        await client.admin.command("ping")
        print(f"Successfully connected to MongoDB! Database: {DATABASE_NAME}")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("MongoDB connection closed")


async def get_database():
    """Get database instance. Auto-connect if not connected."""
    global client
    if client is None:
        await connect_to_mongo()
    return client[DATABASE_NAME]


async def get_users_collection():
    """Get users collection with async client."""
    db = await get_database()
    return db["users"]


async def get_refresh_tokens_collection():
    """Get refresh_tokens collection."""
    db = await get_database()
    return db["refresh_tokens"]


async def get_bookings_collection():
    """Get bookings collection."""
    db = await get_database()
    return db["bookings"]
