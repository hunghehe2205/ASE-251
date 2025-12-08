"""Room booking endpoints."""
from fastapi import APIRouter, Header, HTTPException, status
from datetime import datetime
import uuid

from app.schemas.booking import BookingRequest, BookingResponse, ErrorResponse
from app.database.db_client import get_bookings_collection

router = APIRouter(prefix="/rooms", tags=["bookings"])


async def check_room_availability(
    room_id: str,
    date: str,
    start_time: str,
    end_time: str
) -> bool:
    """Check if room is available for the given time slot."""
    collection = await get_bookings_collection()

    # Find conflicting bookings for the same room and date
    conflicting_booking = await collection.find_one({
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
    })

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
