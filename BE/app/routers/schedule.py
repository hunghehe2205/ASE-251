"""Schedule API endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.services.schedule_service import fetch_from_roms
from app.schemas.schedule import ScheduleResponse

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get("/", response_model=ScheduleResponse)
async def get_schedule(
    room: Optional[str] = Query(None, description="Room ID (e.g., C6-504, 401). Default: all rooms"),
    date: Optional[str] = Query(None, description="Single day in YYYY-MM-DD format"),
    from_date: Optional[str] = Query(None, alias="from", description="Start date in YYYY-MM-DD format"),
    to_date: Optional[str] = Query(None, alias="to", description="End date in YYYY-MM-DD format"),
):
    """
    Get schedule for rooms.
    
    Query behaviors:
    1. /schedule → All rooms from today onwards
    2. /schedule?room=401 → Room 401 from today onwards
    3. /schedule?date=2025-12-10 → All rooms on specific day
    4. /schedule?room=401&date=2025-12-10 → Room 401 on specific day
    5. /schedule?from=2025-12-10&to=2025-12-15 → All rooms in date range
    6. /schedule?room=401&from=2025-12-10&to=2025-12-15 → Room 401 in date range
    7. ?room=all&from=...&to=... → Same as case 5 (all rooms)
    8. ?room=all&date=... → Same as case 3 (all rooms)
    """
    try:
        # Validate date formats
        if date and not _is_valid_date(date):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Bad query parameters - date must be in YYYY-MM-DD format",
                    }
                },
            )
        
        if from_date and not _is_valid_date(from_date):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Bad query parameters - from must be in YYYY-MM-DD format",
                    }
                },
            )
        
        if to_date and not _is_valid_date(to_date):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Bad query parameters - to must be in YYYY-MM-DD format",
                    }
                },
            )
        
        # Fetch schedule data
        schedules = await fetch_from_roms(
            room=room,
            from_date=from_date,
            to_date=to_date,
            date=date,
        )
        
        return ScheduleResponse(data=schedules)
    
    except ValueError as e:
        # Bad request - invalid parameters
        error_msg = str(e)
        if "not found" in error_msg.lower():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "ROOM_NOT_FOUND",
                        "message": f"Room could not be found in ROMS System",
                    }
                },
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": f"Bad query parameters - {error_msg}",
                    }
                },
            )
    
    except Exception as e:
        # ROMS service error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "ROMS_SERVICE_ERROR",
                    "message": "Unable to check room availability",
                }
            },
        )


def _is_valid_date(date_str: str) -> bool:
    """Check if date string is in YYYY-MM-DD format."""
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False
