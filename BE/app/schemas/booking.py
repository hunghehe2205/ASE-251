from pydantic import BaseModel, Field
from typing import Optional


class BookingRequest(BaseModel):
    """Request body for creating a room booking."""
    date: str = Field(..., description="Booking date in YYYY-MM-DD format", example="2025-12-10")
    start_time: str = Field(..., description="Start time in HH:MM format", example="13:00")
    end_time: str = Field(..., description="End time in HH:MM format", example="15:00")
    course_name: str = Field(..., description="Name of the course", example="Data Structures")
    notes: Optional[str] = Field(None, description="Optional notes for the booking", example="Lab session, bilingual")


class BookingResponse(BaseModel):
    """Response for successful booking creation."""
    id: str = Field(..., description="Booking ID")
    room_id: str = Field(..., description="Room ID")
    lecturer_id: str = Field(..., description="Lecturer user ID")
    date: str
    start_time: str
    end_time: str
    course_name: str
    notes: Optional[str] = None
    created_at: str = Field(..., description="ISO timestamp when booking was created")


class ResponseDetail(BaseModel):
    """Error detail structure."""
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ResponseDetail


class SuccessResponse(BaseModel):
    """Standard success response."""
    message: str
