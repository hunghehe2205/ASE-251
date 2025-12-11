"""Schedule schemas for API requests and responses."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ScheduleItem(BaseModel):
    """Single booking entry returned as part of the schedule."""
    booking_id: str = Field(..., description="Booking ID", example="book1")
    room_id: str = Field(..., description="Room ID", example="401")
    user_id: str = Field(..., description="User ID of the lecturer", example="U2025120010")
    date: str = Field(..., description="Booking date in YYYY-MM-DD format", example="2025-12-10")
    start_time: str = Field(..., description="Start time in HH:MM format", example="09:00")
    end_time: str = Field(..., description="End time in HH:MM format", example="11:00")
    course_id: str = Field(..., description="Course ID", example="CO-2017")
    course_name: str = Field(..., description="Course name", example="Data Structures")
    notes: Optional[str] = Field(None, description="Optional notes for the booking", example="Lab session")


class RoomSchedule(BaseModel):
    """Schedule for a single room."""
    room: str = Field(..., description="Room ID", example="401")
    from_date: str = Field(..., alias="from", description="Start date in YYYY-MM-DD format")
    to_date: str = Field(..., alias="to", description="End date in YYYY-MM-DD format")
    booking: List[ScheduleItem] = Field(..., description="List of bookings within the requested range")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "room": "401",
                "from": "2025-12-10",
                "to": "2025-12-15",
                "booking": [
                    {
                        "booking_id": "book1",
                        "room_id": "401",
                        "user_id": "U2025120010",
                        "date": "2025-12-10",
                        "start_time": "09:00",
                        "end_time": "11:00",
                        "course_id": "CO-2017",
                        "course_name": "Data Structures",
                        "notes": "Lab session"
                    }
                ]
            }
        }


class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str
    message: str


class ScheduleErrorResponse(BaseModel):
    """Error response for schedule endpoints."""
    error: ErrorDetail
