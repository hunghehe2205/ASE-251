"""Schedule API endpoints."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Query
from datetime import datetime, timedelta

from app.schemas.schedule import RoomSchedule, ScheduleItem, ScheduleErrorResponse

router = APIRouter(prefix="/schedule", tags=["Schedule"])


async def fetch_schedule_from_roms(
    room: Optional[str],
    from_date: str,
    to_date: str
) -> List[RoomSchedule]:
    """
    Fetch schedule data from ROMS service.
    
    Args:
        room: Room ID or None for all rooms
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
    
    Returns:
        List of RoomSchedule objects
    
    Raises:
        ValueError: If room not found
        Exception: For ROMS service errors
    """
    # TODO: Replace with actual ROMS API call
    # For now, return mock data
    
    mock_rooms = ["401", "402", "C6-504", "C6-505"]
    
    # If specific room requested, validate it exists
    if room and room not in mock_rooms:
        raise ValueError(f"Room {room} not found")
    
    # Determine which rooms to return
    rooms_to_return = [room] if room else mock_rooms
    
    result = []
    for room_id in rooms_to_return:
        result.append(
            RoomSchedule(
                room=room_id,
                **{
                    "from": from_date,
                    "to": to_date
                },
                booking=[
                    ScheduleItem(
                        booking_id=f"{room_id}-bk-1",
                        room_id=room_id,
                        user_id="U2025120010",
                        date=from_date,
                        start_time="09:00",
                        end_time="11:00",
                        course_id="CO-2017",
                        course_name="Data Structures",
                        notes="Mock data from ROMS"
                    )
                ]
            )
        )
    
    return result


@router.get(
    "/",
    response_model=List[RoomSchedule],
    responses={
        200: {
            "description": "Successfully retrieved schedule",
            "model": List[RoomSchedule]
        },
        400: {
            "description": "Bad request - Invalid query parameters",
            "model": ScheduleErrorResponse
        },
        404: {
            "description": "Room not found",
            "model": ScheduleErrorResponse
        },
        500: {
            "description": "ROMS service error",
            "model": ScheduleErrorResponse
        }
    }
)
async def get_schedule(
    room: Optional[str] = Query(
        None,
        description="Room ID (e.g., C6-504, 401). Default: all rooms",
        example="401"
    ),
    date: Optional[str] = Query(
        None,
        description="Single day in YYYY-MM-DD format",
        example="2025-12-10"
    ),
    from_date: Optional[str] = Query(
        None,
        alias="from",
        description="Start date in YYYY-MM-DD format",
        example="2025-12-10"
    ),
    to_date: Optional[str] = Query(
        None,
        alias="to",
        description="End date in YYYY-MM-DD format",
        example="2025-12-15"
    ),
):
    """
    Get schedule for rooms.
    
    **Query Behaviors:**
    1. `/schedule` → All rooms from today onwards
    2. `/schedule?room=401` → Room 401 from today onwards
    3. `/schedule?date=2025-12-10` → All rooms on specific day
    4. `/schedule?room=401&date=2025-12-10` → Room 401 on specific day
    5. `/schedule?from=2025-12-10&to=2025-12-15` → All rooms in date range
    6. `/schedule?room=401&from=2025-12-10&to=2025-12-15` → Room 401 in date range
    7. `/schedule?room=all&from=...&to=...` → Same as case 5 (all rooms)
    8. `/schedule?room=all&date=...` → Same as case 3 (all rooms)
    
    **Rules:**
    - If `from` and `to` exist → ignore `date`
    - If only `date` exists → return single day schedule
    - `room=all` is treated as requesting all rooms
    """
    try:
        # Validate date formats
        if date and not _is_valid_date_format(date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Bad query parameters - date must be in YYYY-MM-DD format"
                    }
                }
            )
        
        if from_date and not _is_valid_date_format(from_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Bad query parameters - from must be in YYYY-MM-DD format"
                    }
                }
            )
        
        if to_date and not _is_valid_date_format(to_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Bad query parameters - to must be in YYYY-MM-DD format"
                    }
                }
            )
        
        # Determine date range based on query parameters
        today = datetime.now().date()
        
        if from_date and to_date:
            # Case 5, 6, 7: Date range provided (ignore date parameter)
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
            
            if start_date > end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": {
                            "code": "BAD_REQUEST",
                            "message": "Bad query parameters - from date cannot be later than to date"
                        }
                    }
                )
        elif date:
            # Case 3, 4, 8: Single day
            start_date = datetime.strptime(date, "%Y-%m-%d").date()
            end_date = start_date
        else:
            # Case 1, 2: Default - from today onwards (30 days ahead)
            start_date = today
            end_date = today + timedelta(days=30)
        
        # Handle room parameter
        room_id = None
        if room and room.lower() != "all":
            room_id = room
        
        # Fetch schedule data
        schedules = await fetch_schedule_from_roms(
            room=room_id,
            from_date=start_date.strftime("%Y-%m-%d"),
            to_date=end_date.strftime("%Y-%m-%d")
        )
        
        return schedules
    
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    
    except ValueError as e:
        # Room not found or other validation error
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "ROOM_NOT_FOUND",
                        "message": "Room could not be found in ROMS System"
                    }
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Bad query parameters"
                    }
                }
            )
    
    except Exception as e:
        # ROMS service error or other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "ROMS_SERVICE_ERROR",
                    "message": "Unable to check room availability"
                }
            }
        )


def _is_valid_date_format(date_str: str) -> bool:
    """Validate date string is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False
