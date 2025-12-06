from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from app.config.settings import MONGODB_URL, DATABASE_NAME

# Global client instance
client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo():
    """Connect to MongoDB."""
    global client
    try:
        # Add TLS/SSL configuration for MongoDB Atlas
        client = AsyncIOMotorClient(
            MONGODB_URL
        )
        # Test the connection
        await client.admin.command('ping')
        print(
            f"Successfully connected to MongoDB! Database: {DATABASE_NAME}")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print(" MongoDB connection closed")


async def get_database():
    """Get database instance. Auto-connect if not connected."""
    global client
    if client is None:
        await connect_to_mongo()
    return client[DATABASE_NAME]


def get_users_collection():
    """Get users collection."""
    global client
    if client is None:
        # Return a lazy client that will connect on first use
        client = AsyncIOMotorClient(
            MONGODB_URL
        )
    return client[DATABASE_NAME]["users"]
