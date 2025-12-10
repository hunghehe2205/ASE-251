"""Schedule schemas for API requests and responses."""
from typing import List
from pydantic import BaseModel, Field


class ScheduleItem(BaseModel):
    """Single schedule entry."""
    date: str = Field(..., description="Date in YYYY-MM-DD format", example="2025-12-10")
    start_time: str = Field(..., description="Start time in HH:MM format", example="09:00")
    end_time: str = Field(..., description="End time in HH:MM format", example="11:00")
    course_name: str = Field(..., description="Course name", example="Data Structures")
    lecturer: str = Field(..., description="Lecturer name", example="Nguyen A")


class RoomSchedule(BaseModel):
    """Schedule for a single room."""
    room: str = Field(..., description="Room ID", example="401")
    from_date: str = Field(..., alias="from", description="Start date in YYYY-MM-DD format")
    to_date: str = Field(..., alias="to", description="End date in YYYY-MM-DD format")
    schedule: List[ScheduleItem] = Field(..., description="List of schedule items")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "room": "401",
                "from": "2025-12-10",
                "to": "2025-12-15",
                "schedule": [
                    {
                        "date": "2025-12-10",
                        "start_time": "09:00",
                        "end_time": "11:00",
                        "course_name": "Data Structures",
                        "lecturer": "Nguyen A"
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
