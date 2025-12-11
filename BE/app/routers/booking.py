"""Room booking endpoints."""
from fastapi import APIRouter, Header, HTTPException, status
from datetime import datetime, date, time, timedelta
import uuid
import re
import asyncio
from typing import Optional

from app.schemas.booking import BookingRequest, BookingUpdateRequest, BookingResponse, ErrorResponse, SuccessResponse
from app.database.db_client import get_bookings_collection

router = APIRouter(prefix="/rooms", tags=["bookings"])

# Regex patterns for date/time validation
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TIME_PATTERN = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')


def validate_date_time_format(booking_date: str, start_time: str, end_time: str) -> tuple[date, time, time]:
    """
    Validate date and time formats using regex and datetime parsing.

    Returns:
        tuple: (date_obj, start_time_obj, end_time_obj)

    Raises:
        HTTPException: If format validation fails
    """
    # Regex validation first
    if not DATE_PATTERN.match(booking_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_DATE_FORMAT",
                    "message": "Date must be in YYYY-MM-DD format"
                }
            }
        )

    if not TIME_PATTERN.match(start_time):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_START_TIME_FORMAT",
                    "message": "Start time must be in HH:MM format (24-hour)"
                }
            }
        )

    if not TIME_PATTERN.match(end_time):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_END_TIME_FORMAT",
                    "message": "End time must be in HH:MM format (24-hour)"
                }
            }
        )

    # Datetime parsing validation
    try:
        date_obj = datetime.strptime(booking_date, "%Y-%m-%d").date()
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()
        return date_obj, start_time_obj, end_time_obj
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_DATE_TIME_VALUE",
                    "message": f"Invalid date or time value: {str(e)}"
                }
            }
        )


def validate_booking_business_logic(
    booking_date: str,
    start_time: str,
    end_time: str,
    max_duration_days: int = 30
) -> None:
    """
    Validate booking business logic rules with enhanced format validation.

    Rules:
    1. Format validation (YYYY-MM-DD, HH:MM) with regex + datetime parsing
    2. start_time must be before end_time (accurate datetime comparison)
    3. booking date cannot be in the past
    4. booking duration cannot exceed max_duration_days (default: 30 days)

    Raises HTTPException if validation fails.
    """
    # Step 1: Validate formats and parse to datetime objects
    booking_date_obj, start_time_obj, end_time_obj = validate_date_time_format(
        booking_date, start_time, end_time
    )

    # Step 2: Create full datetime objects for accurate comparison
    booking_start_datetime = datetime.combine(booking_date_obj, start_time_obj)
    booking_end_datetime = datetime.combine(booking_date_obj, end_time_obj)

    # Rule 1: start_time < end_time (accurate datetime comparison)
    if booking_start_datetime >= booking_end_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_TIME_RANGE",
                    "message": "Start time must be before end time"
                }
            }
        )

    # Rule 2: booking not in past
    today = date.today()
    if booking_date_obj < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BOOKING_IN_PAST",
                    "message": "Cannot create booking for past dates"
                }
            }
        )

    # Rule 3: max duration check
    max_future_date = today + timedelta(days=max_duration_days)
    if booking_date_obj > max_future_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BOOKING_TOO_FAR_FUTURE",
                    "message": f"Cannot create booking more than {max_duration_days} days in advance"
                }
            }
        )


async def retry_db_operation(operation, max_retries: int = 3, delay: float = 0.1):
    """
    Retry database operations with exponential backoff.

    Args:
        operation: Async function to retry
        max_retries: Maximum number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 0.1)

    Returns:
        Result of the operation

    Raises:
        HTTPException: If all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                # Exponential backoff: 0.1s, 0.2s, 0.4s
                await asyncio.sleep(delay * (2 ** attempt))
                continue
            else:
                # All retries failed
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": {
                            "code": "DATABASE_OPERATION_FAILED",
                            "message": f"Database operation failed after {max_retries} retries: {str(last_exception)}"
                        }
                    }
                )


class BookingDatabaseOperations:
    """Centralized database operations with timeout and retry logic."""

    @staticmethod
    async def find_booking_by_id(booking_id: str, room_id: str = None) -> dict:
        """Find booking with retry and timeout."""
        async def find_operation():
            collection = await get_bookings_collection()
            query = {"booking_id": booking_id}
            if room_id:
                query["room_id"] = room_id
            return await asyncio.wait_for(
                collection.find_one(query),
                timeout=3.0
            )

        return await retry_db_operation(find_operation)

    @staticmethod
    async def insert_booking(booking_doc: dict) -> None:
        """Insert booking with retry and timeout."""
        async def insert_operation():
            collection = await get_bookings_collection()
            return await asyncio.wait_for(
                collection.insert_one(booking_doc),
                timeout=3.0
            )

        await retry_db_operation(insert_operation)

    @staticmethod
    async def update_booking(booking_id: str, room_id: str, update_doc: dict) -> None:
        """Update booking with retry and timeout."""
        async def update_operation():
            collection = await get_bookings_collection()
            return await asyncio.wait_for(
                collection.update_one(
                    {"booking_id": booking_id, "room_id": room_id},
                    {"$set": update_doc}
                ),
                timeout=3.0
            )

        await retry_db_operation(update_operation)

    @staticmethod
    async def delete_booking(booking_id: str, room_id: str) -> None:
        """Delete booking with retry and timeout."""
        async def delete_operation():
            collection = await get_bookings_collection()
            return await asyncio.wait_for(
                collection.delete_one({
                    "booking_id": booking_id,
                    "room_id": room_id
                }),
                timeout=3.0
            )

        await retry_db_operation(delete_operation)


class BookingValidator:
    """Centralized validation logic for bookings."""

    @staticmethod
    def validate_and_parse_booking_data(booking_date: str, start_time: str, end_time: str) -> tuple[date, time, time]:
        """Complete validation and parsing of booking data."""
        # Step 1: Format validation and parsing
        date_obj, start_time_obj, end_time_obj = validate_date_time_format(
            booking_date, start_time, end_time
        )

        # Step 2: Business logic validation
        validate_booking_business_logic(booking_date, start_time, end_time)

        return date_obj, start_time_obj, end_time_obj

    @staticmethod
    async def validate_room_availability(room_id: str, date: str, start_time: str, end_time: str, exclude_booking_id: str = None) -> None:
        """Validate room availability and raise exception if not available."""
        is_available = await check_room_availability(
            room_id=room_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            exclude_booking_id=exclude_booking_id,
            timeout=5.0
        )

        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "ROOM_ALREADY_BOOKED",
                        "message": f"Room is not available from {start_time} to {end_time}"
                    }
                }
            )

    @staticmethod
    def validate_user_authorization(role: str, required_role: str = "lecturer") -> None:
        """Validate user role authorization."""
        if role != required_role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": f"Only {required_role}s can perform this action"
                    }
                }
            )

    @staticmethod
    def validate_booking_ownership(existing_booking: dict, user_id: str) -> None:
        """Validate that user owns the booking."""
        if existing_booking["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDEN_ACTION",
                        "message": "Only creator can UPDATE / DELETE booking"
                    }
                }
            )


class BookingResponseBuilder:
    """Centralized response building for bookings."""

    @staticmethod
    def build_booking_response(booking_data: dict) -> BookingResponse:
        """Build standardized booking response."""
        return BookingResponse(
            booking_id=booking_data["booking_id"],
            room_id=booking_data["room_id"],
            user_id=booking_data["user_id"],
            date=booking_data["date"],
            start_time=booking_data["start_time"],
            end_time=booking_data["end_time"],
            course_id=booking_data["course_id"],
            course_name=booking_data["course_name"],
            notes=booking_data.get("notes")
        )


async def check_room_availability(
    room_id: str,
    date: str,
    start_time: str,
    end_time: str,
    exclude_booking_id: str = None,
    timeout: float = 5.0
) -> bool:
    """
    Check if room is available for the given time slot with timeout.

    Args:
        room_id: Room identifier
        date: Booking date (YYYY-MM-DD)
        start_time: Start time (HH:MM)
        end_time: End time (HH:MM)
        exclude_booking_id: Booking ID to exclude from conflict check
        timeout: Query timeout in seconds (default: 5.0)

    Returns:
        bool: True if room is available, False if conflicted

    Raises:
        HTTPException: If query times out or fails
    """
    async def availability_check():
        collection = await get_bookings_collection()

        # Build query to find conflicting bookings
        query = {
            "room_id": room_id,
            "date": date,
            "$or": [
                # New booking starts during an existing booking
                {
                    "start_time": {"$lte": start_time},
                    "end_time": {"$gt": start_time}
                },
                # New booking ends during an existing booking
                {
                    "start_time": {"$lt": end_time},
                    "end_time": {"$gte": end_time}
                },
                # New booking completely contains an existing booking
                {
                    "start_time": {"$gte": start_time},
                    "end_time": {"$lte": end_time}
                }
            ]
        }

        # Exclude the current booking when updating
        if exclude_booking_id:
            query["booking_id"] = {"$ne": exclude_booking_id}

        conflicting_booking = await collection.find_one(query)
        return conflicting_booking is None

    try:
        # Apply timeout to availability check
        return await asyncio.wait_for(availability_check(), timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={
                "error": {
                    "code": "AVAILABILITY_CHECK_TIMEOUT",
                    "message": f"Room availability check timed out after {timeout} seconds"
                }
            }
        )


@router.post(
    "/{room_id}/booking",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "model": BookingResponse,
            "description": "Booking created successfully"
        },
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - Invalid booking data (time range, past date, or too far future)"
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Only lecturers can create bookings"
        },
        408: {
            "model": ErrorResponse,
            "description": "Request Timeout - Database operation timed out"
        },
        409: {
            "model": ErrorResponse,
            "description": "Conflict - Room is already booked for this time"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def create_booking(
    room_id: str,
    booking_data: BookingRequest,
    role: str = Header(default="")
):
    """
    Create a new room booking.

    - **room_id**: Room identifier (e.g., "401")
    - **user_id**: User ID of the lecturer
    - **date**: Booking date in YYYY-MM-DD format
    - **start_time**: Start time in HH:MM format
    - **end_time**: End time in HH:MM format
    - **course_id**: Course ID
    - **course_name**: Name of the course
    - **notes**: Optional notes about the booking

    Requires role header with value "lecturer".
    Returns the created booking with auto-generated booking_id.
    """
    try:
        # Step 1: Validate user authorization
        BookingValidator.validate_user_authorization(role, "lecturer")

        # Step 2: Validate and parse booking data (format + business logic)
        BookingValidator.validate_and_parse_booking_data(
            booking_data.date,
            booking_data.start_time,
            booking_data.end_time
        )

        # Step 3: Validate room availability
        await BookingValidator.validate_room_availability(
            room_id=room_id,
            date=booking_data.date,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time
        )
        # Step 4: Generate booking ID and create document
        booking_id = f"book{str(uuid.uuid4())[:8]}"

        booking_doc = {
            "booking_id": booking_id,
            "room_id": room_id,
            "user_id": booking_data.user_id,
            "date": booking_data.date,
            "start_time": booking_data.start_time,
            "end_time": booking_data.end_time,
            "course_id": booking_data.course_id,
            "course_name": booking_data.course_name,
            "notes": booking_data.notes,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        # Step 5: Insert booking using centralized database operations
        await BookingDatabaseOperations.insert_booking(booking_doc)

        # Step 6: Return standardized response
        return BookingResponseBuilder.build_booking_response(booking_doc)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "ROMS_SERVICE_ERROR",
                    "message": "Unable to check room availability"
                }
            }
        )


@router.put(
    "/{room_id}/booking/{booking_id}",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "model": BookingResponse,
            "description": "Booking updated successfully"
        },
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - Invalid booking data (time range, past date, or too far future)"
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Only lecturers can update bookings"
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Only creator can update booking"
        },
        404: {
            "model": ErrorResponse,
            "description": "Booking not found"
        },
        405: {
            "model": ErrorResponse,
            "description": "Room service timeout"
        },
        408: {
            "model": ErrorResponse,
            "description": "Request Timeout - Database operation timed out"
        },
        409: {
            "model": ErrorResponse,
            "description": "Conflict - Room is already booked for this time"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def update_booking(
    room_id: str,
    booking_id: str,
    booking_data: BookingUpdateRequest,
    user_id: str = Header(...),
    role: str = Header(default="")
):
    """
    Update an existing room booking.

    - **room_id**: Room identifier
    - **booking_id**: Booking identifier to update
    - **user_id**: User ID in header (must match booking creator)
    - **role**: User role in header (must be "lecturer")

    Only the original creator can update their booking.
    """
    try:
        # Step 1: Validate user authorization
        BookingValidator.validate_user_authorization(role, "lecturer")

        # Step 2: Find existing booking
        existing_booking = await BookingDatabaseOperations.find_booking_by_id(booking_id, room_id)

        if not existing_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "BOOKING_NOT_FOUND",
                        "message": "Booking ID could not be found in ROMs System"
                    }
                }
            )

        # Step 3: Validate booking ownership
        BookingValidator.validate_booking_ownership(existing_booking, user_id)

        # Step 4: Merge update data with existing booking
        updated_data = {
            "user_id": booking_data.user_id if booking_data.user_id is not None else existing_booking["user_id"],
            "date": booking_data.date if booking_data.date is not None else existing_booking["date"],
            "start_time": booking_data.start_time if booking_data.start_time is not None else existing_booking["start_time"],
            "end_time": booking_data.end_time if booking_data.end_time is not None else existing_booking["end_time"],
            "course_id": booking_data.course_id if booking_data.course_id is not None else existing_booking["course_id"],
            "course_name": booking_data.course_name if booking_data.course_name is not None else existing_booking["course_name"],
            "notes": booking_data.notes if booking_data.notes is not None else existing_booking.get("notes")
        }

        # Step 5: Validate updated data (format + business logic)
        BookingValidator.validate_and_parse_booking_data(
            updated_data["date"],
            updated_data["start_time"],
            updated_data["end_time"]
        )

        # Step 6: Check room availability if time/date changed
        if (booking_data.date is not None or booking_data.start_time is not None or booking_data.end_time is not None):
            await BookingValidator.validate_room_availability(
                room_id=room_id,
                date=updated_data["date"],
                start_time=updated_data["start_time"],
                end_time=updated_data["end_time"],
                exclude_booking_id=booking_id
            )

        # Step 7: Prepare update document
        update_doc = {
            **updated_data,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

        # Step 8: Update booking using centralized database operations
        await BookingDatabaseOperations.update_booking(booking_id, room_id, update_doc)

        # Step 9: Return standardized response
        return BookingResponseBuilder.build_booking_response(updated_data)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors - could be room service timeout
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail={
                "error": {
                    "code": "ROOM_SERVICE_TIMEOUT",
                    "message": "Room system did not respond"
                }
            }
        )


@router.get(
    "/booking/{booking_id}",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "model": BookingResponse,
            "description": "Booking retrieved successfully"
        },
        404: {
            "model": ErrorResponse,
            "description": "Booking not found"
        },
        408: {
            "model": ErrorResponse,
            "description": "Request Timeout - Database operation timed out"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def get_booking(
    booking_id: str
):
    """
    Get booking information by booking ID.

    - **booking_id**: Booking identifier to retrieve

    Returns the booking details including room_id if found.
    """
    try:
        # Step 1: Find booking using centralized database operations
        booking = await BookingDatabaseOperations.find_booking_by_id(booking_id)

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "BOOKING_NOT_FOUND",
                        "message": "Booking ID could not be found in ROMs System"
                    }
                }
            )

        # Step 2: Return standardized response
        return BookingResponseBuilder.build_booking_response(booking)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Unable to retrieve booking information"
                }
            }
        )


@router.delete(
    "/{room_id}/booking/{booking_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "model": SuccessResponse,
            "description": "Booking deleted successfully"
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Only lecturers can delete bookings"
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Only creator can delete booking"
        },
        404: {
            "model": ErrorResponse,
            "description": "Booking not found"
        },
        405: {
            "model": ErrorResponse,
            "description": "Room service timeout"
        },
        408: {
            "model": ErrorResponse,
            "description": "Request Timeout - Database operation timed out"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def delete_booking(
    room_id: str,
    booking_id: str,
    user_id: str = Header(...),
    role: str = Header(default="")
):
    """
    Delete an existing room booking.

    - **room_id**: Room identifier
    - **booking_id**: Booking identifier to delete
    - **user_id**: User ID in header (must match booking creator)
    - **role**: User role in header (must be "lecturer")

    Only the original creator can delete their booking.
    """
    try:
        # Step 1: Validate user authorization
        BookingValidator.validate_user_authorization(role, "lecturer")

        # Step 2: Find existing booking
        existing_booking = await BookingDatabaseOperations.find_booking_by_id(booking_id, room_id)

        if not existing_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "BOOKING_NOT_FOUND",
                        "message": "Booking ID could not be found in ROMs System"
                    }
                }
            )

        # Step 3: Validate booking ownership
        BookingValidator.validate_booking_ownership(existing_booking, user_id)

        # Step 4: Delete booking using centralized database operations
        await BookingDatabaseOperations.delete_booking(booking_id, room_id)

        # Return success message
        return SuccessResponse(message="Delete successfully")

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors - could be room service timeout
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail={
                "error": {
                    "code": "ROOM_SERVICE_TIMEOUT",
                    "message": "Room system did not respond"
                }
            }
        )
