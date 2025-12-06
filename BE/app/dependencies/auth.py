"""Simple header-based authentication and authorization."""
from fastapi import Header, HTTPException, status
from typing import Optional

async def require_lecturer(role: str = Header(...)) -> None:
    """
    Ensure the current user is a lecturer.
    
    Expected header: role: lecturer
    """
    if role != "lecturer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Only lecturers can create room bookings"
                }
            }
        )
