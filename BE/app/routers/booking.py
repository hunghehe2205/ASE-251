"""Room booking endpoints."""
from fastapi import APIRouter, Header, HTTPException, status
from datetime import datetime
import uuid

from app.schemas.booking import BookingRequest, BookingUpdateRequest, BookingResponse, ErrorResponse, SuccessResponse
from app.database.db_client import get_bookings_collection

router = APIRouter(prefix="/rooms", tags=["bookings"])


async def check_room_availability(
    room_id: str,
    date: str,
    start_time: str,
    end_time: str,
    exclude_booking_id: str = None
) -> bool:
    """Check if room is available for the given time slot."""
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


@router.post(
    "/{room_id}/booking",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "model": BookingResponse,
            "description": "Booking created successfully"
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Only lecturers can create bookings"
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
    # Check if role is lecturer
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

    try:
        # Check room availability
        is_available = await check_room_availability(
            room_id=room_id,
            date=booking_data.date,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time
        )
        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "ROOM_ALREADY_BOOKED",
                        "message": f"Room is not available from {booking_data.start_time} to {booking_data.end_time}"
                    }
                }
            )
        # Generate booking ID
        booking_id = f"book{str(uuid.uuid4())[:8]}"

        # Create booking document
        collection = await get_bookings_collection()
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

        await collection.insert_one(booking_doc)

        # Return full booking response
        return BookingResponse(
            booking_id=booking_id,
            room_id=room_id,
            user_id=booking_data.user_id,
            date=booking_data.date,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            course_id=booking_data.course_id,
            course_name=booking_data.course_name,
            notes=booking_data.notes
        )

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
    # Check if role is lecturer
    if role != "lecturer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Only lecturers can update room bookings"
                }
            }
        )

    try:
        collection = await get_bookings_collection()

        # Find existing booking
        existing_booking = await collection.find_one({
            "booking_id": booking_id,
            "room_id": room_id
        })

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

        # Check if user is the creator
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

        # Merge update data with existing booking (only update provided fields)
        updated_data = {
            "user_id": booking_data.user_id if booking_data.user_id is not None else existing_booking["user_id"],
            "date": booking_data.date if booking_data.date is not None else existing_booking["date"],
            "start_time": booking_data.start_time if booking_data.start_time is not None else existing_booking["start_time"],
            "end_time": booking_data.end_time if booking_data.end_time is not None else existing_booking["end_time"],
            "course_id": booking_data.course_id if booking_data.course_id is not None else existing_booking["course_id"],
            "course_name": booking_data.course_name if booking_data.course_name is not None else existing_booking["course_name"],
            "notes": booking_data.notes if booking_data.notes is not None else existing_booking.get("notes")
        }

        # Check room availability (excluding current booking) only if time/date changed
        if (booking_data.date is not None or booking_data.start_time is not None or booking_data.end_time is not None):
            is_available = await check_room_availability(
                room_id=room_id,
                date=updated_data["date"],
                start_time=updated_data["start_time"],
                end_time=updated_data["end_time"],
                exclude_booking_id=booking_id
            )

            if not is_available:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": {
                            "code": "ROOM_ALREADY_BOOKED",
                            "message": f"Room is not available from {updated_data['start_time']} to {updated_data['end_time']}"
                        }
                    }
                )

        # Update booking document with only changed fields
        update_doc = {
            "user_id": updated_data["user_id"],
            "date": updated_data["date"],
            "start_time": updated_data["start_time"],
            "end_time": updated_data["end_time"],
            "course_id": updated_data["course_id"],
            "course_name": updated_data["course_name"],
            "notes": updated_data["notes"],
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

        await collection.update_one(
            {"booking_id": booking_id, "room_id": room_id},
            {"$set": update_doc}
        )

        # Return updated booking response
        return BookingResponse(
            booking_id=booking_id,
            room_id=room_id,
            user_id=updated_data["user_id"],
            date=updated_data["date"],
            start_time=updated_data["start_time"],
            end_time=updated_data["end_time"],
            course_id=updated_data["course_id"],
            course_name=updated_data["course_name"],
            notes=updated_data["notes"]
        )

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
        collection = await get_bookings_collection()

        # Find the booking by booking_id only
        booking = await collection.find_one({
            "booking_id": booking_id
        })

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

        # Return booking response including room_id
        return BookingResponse(
            booking_id=booking["booking_id"],
            room_id=booking["room_id"],
            user_id=booking["user_id"],
            date=booking["date"],
            start_time=booking["start_time"],
            end_time=booking["end_time"],
            course_id=booking["course_id"],
            course_name=booking["course_name"],
            notes=booking.get("notes")
        )

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
    # Check if role is lecturer
    if role != "lecturer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Only lecturers can delete room bookings"
                }
            }
        )

    try:
        collection = await get_bookings_collection()

        # Find existing booking
        existing_booking = await collection.find_one({
            "booking_id": booking_id,
            "room_id": room_id
        })

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

        # Check if user is the creator
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

        # Delete the booking
        await collection.delete_one({
            "booking_id": booking_id,
            "room_id": room_id
        })

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
