from typing import List, Optional
from pydantic import BaseModel, Field


class ScheduleItem(BaseModel):
    """Single schedule entry."""
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    course_name: str
    lecturer: str


class RoomSchedule(BaseModel):
    """Schedule for a single room."""
    room: str
    from_date: str = Field(alias="from")  # YYYY-MM-DD
    to_date: str = Field(alias="to")  # YYYY-MM-DD
    schedule: List[ScheduleItem]

    class Config:
        allow_population_by_field_name = True


class ScheduleResponse(BaseModel):
    """Response body for schedule endpoint."""
    data: List[RoomSchedule]


class ErrorResponse(BaseModel):
    """Error response body."""
    error: dict
