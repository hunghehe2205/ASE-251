from fastapi import APIRouter

router = APIRouter()


@router.get("/health_check")
async def health_check():
    """Simple health check endpoint to verify the API is running."""
    return {"status": "healthy"}
