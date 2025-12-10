from pydantic import BaseModel, Field
from typing import Optional


class BookingRequest(BaseModel):
    """Request body for creating a room booking."""
    user_id: str = Field(..., description="User ID of the lecturer",
                         example="U2025120010")
    date: str = Field(..., description="Booking date in YYYY-MM-DD format",
                      example="2025-12-10")
    start_time: str = Field(...,
                            description="Start time in HH:MM format", example="13:00")
    end_time: str = Field(...,
                          description="End time in HH:MM format", example="15:00")
    course_id: str = Field(..., description="Course ID", example="CO-2017")
    course_name: str = Field(..., description="Name of the course",
                             example="Data Structure & Algorithm")
    notes: Optional[str] = Field(
        None, description="Optional notes for the booking", example="Lab session, bilingual")


class BookingUpdateRequest(BaseModel):
    """Request body for updating a room booking - all fields optional."""
    user_id: Optional[str] = Field(None, description="User ID of the lecturer",
                                   example="U2025120010")
    date: Optional[str] = Field(None, description="Booking date in YYYY-MM-DD format",
                                example="2025-12-10")
    start_time: Optional[str] = Field(None,
                                      description="Start time in HH:MM format", example="13:00")
    end_time: Optional[str] = Field(None,
                                    description="End time in HH:MM format", example="15:00")
    course_id: Optional[str] = Field(
        None, description="Course ID", example="CO-2017")
    course_name: Optional[str] = Field(None, description="Name of the course",
                                       example="Data Structure & Algorithm")
    notes: Optional[str] = Field(
        None, description="Optional notes for the booking", example="Lab session, bilingual")


class BookingResponse(BaseModel):
    """Response for successful booking creation."""
    booking_id: str = Field(..., description="Booking ID")
    user_id: str = Field(..., description="User ID of the lecturer")
    date: str
    start_time: str
    end_time: str
    course_id: str
    course_name: str
    notes: Optional[str] = None


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
