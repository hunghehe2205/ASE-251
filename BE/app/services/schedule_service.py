"""Schedule service to fetch and process ROMS schedule data."""
from datetime import datetime, timedelta
from typing import List, Optional
import httpx
from app.schemas.schedule import RoomSchedule, ScheduleItem


async def fetch_from_roms(
    room: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    date: Optional[str] = None,
) -> List[RoomSchedule]:
    """
    Fetch schedule data from ROMS service.
    
    Args:
        room: Room ID (e.g., 'C6-504', '401'). If "all" or None → all rooms
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
        date: Single date in YYYY-MM-DD format
    
    Returns:
        List of RoomSchedule objects
    
    Raises:
        ValueError: For bad query parameters
        Exception: For ROMS service errors
    """
    
    # Validate and determine date range
    today = datetime.now().date()
    
    if from_date and to_date:
        # Date range provided
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d").date()
            end = datetime.strptime(to_date, "%Y-%m-%d").date()
            if start > end:
                raise ValueError("from date cannot be later than to date")
        except ValueError as e:
            raise ValueError(f"Invalid date format or range: {str(e)}")
    elif date:
        # Single day provided
        try:
            start = datetime.strptime(date, "%Y-%m-%d").date()
            end = start
        except ValueError:
            raise ValueError("Invalid date format")
    else:
        # No date provided → from today onwards (1 month ahead for default)
        start = today
        end = today + timedelta(days=30)
    
    # Validate room parameter
    room_id = None
    if room and room.lower() != "all":
        room_id = room
        # Basic validation: room should not be empty string after strip
        if not room_id.strip():
            raise ValueError("Invalid room ID")
    
    # TODO: Call actual ROMS API endpoint here
    # For now, return mock data structure
    # In production, this would call: GET /roms/schedule?room={room}&from={from}&to={to}
    
    mock_response = [
        RoomSchedule(
            room="401",
            **{
                "from": start.strftime("%Y-%m-%d"),
                "to": end.strftime("%Y-%m-%d"),
            },
            schedule=[
                ScheduleItem(
                    date=start.strftime("%Y-%m-%d"),
                    start_time="09:00",
                    end_time="11:00",
                    course_name="Data Structures",
                    lecturer="Nguyen A",
                )
            ],
        ),
        RoomSchedule(
            room="402",
            **{
                "from": start.strftime("%Y-%m-%d"),
                "to": end.strftime("%Y-%m-%d"),
            },
            schedule=[
                ScheduleItem(
                    date=start.strftime("%Y-%m-%d"),
                    start_time="09:00",
                    end_time="11:00",
                    course_name="Data Structures",
                    lecturer="Nguyen A",
                )
            ],
        ),
    ]
    
    # Filter by room if specified
    if room_id:
        mock_response = [r for r in mock_response if r.room == room_id]
        if not mock_response:
            raise ValueError(f"Room {room_id} not found")
    
    return mock_response
