from fastapi import APIRouter, HTTPException, status
from app.database.db_client import connect_to_mongo, close_mongo_connection

router = APIRouter()


@router.get("/health_check")
async def health_check():
    """Simple health check endpoint to verify the API is running."""
    return {"status": "healthy"}


@router.get("/health_check/database")
async def database_health_check():
    """Check database connection status."""
    try:
        await connect_to_mongo()
        return {
            "status": "success",
            "message": "Database connected successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )
