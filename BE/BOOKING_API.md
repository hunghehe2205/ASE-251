# Booking API Documentation

## Overview
The Booking API allows lecturers to create room bookings with time conflict checking and proper authorization.

## Endpoint

### Create Room Booking
```
POST /rooms/{room_id}/booking
```

Creates a new booking for a specific room.

## Authentication
Requires JWT Bearer token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

**Role Required:** `lecturer` (only lecturers can create bookings)

## Request

### Path Parameters
- `room_id` (string): The room identifier (e.g., "401")

### Request Body
```json
{
  "date": "2025-12-10",           // String, required (YYYY-MM-DD format)
  "start_time": "13:00",          // String, required (HH:MM format)
  "end_time": "15:00",            // String, required (HH:MM format)
  "course_name": "Data Structures", // String, required
  "notes": "Lab session, bilingual" // String, optional
}
```

## Responses

### ✅ Success (201 Created)
```json
{
  "id": "674e3f12a5b8c9d8e7f6a1b2",
  "room_id": "401",
  "lecturer_id": "lecturer_001",
  "date": "2025-12-10",
  "start_time": "13:00",
  "end_time": "15:00",
  "course_name": "Data Structures",
  "notes": "Lab session, bilingual",
  "created_at": "2025-12-06T10:30:00Z"
}
```

### ❌ Unauthorized (401)
When a non-lecturer tries to create a booking:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Only lecturers can create room bookings"
  }
}
```

### ❌ Time Conflict (409)
When the room is already booked for the requested time:
```json
{
  "error": {
    "code": "ROOM_ALREADY_BOOKED",
    "message": "Room is not available from 13:00 to 15:00"
  }
}
```

### ❌ Internal Server Error (500)
When there's a problem checking room availability:
```json
{
  "error": {
    "code": "ROMS_SERVICE_ERROR",
    "message": "Unable to check room availability"
  }
}
```

## Implementation Details

### Files Created
1. **`app/schemas/booking.py`** - Pydantic models for request/response
2. **`app/dependencies/auth.py`** - JWT authentication and authorization
3. **`app/routers/booking.py`** - Booking endpoint implementation
4. **`app/database/db_client.py`** - Added `get_bookings_collection()` function

### Time Conflict Detection
The API checks for overlapping bookings using MongoDB queries:
- New booking starts during an existing booking
- New booking ends during an existing booking
- New booking completely contains an existing booking

### Database Schema
Bookings are stored in the `bookings` collection:
```json
{
  "_id": ObjectId,
  "room_id": "401",
  "lecturer_id": "lecturer_001",
  "date": "2025-12-10",
  "start_time": "13:00",
  "end_time": "15:00",
  "course_name": "Data Structures",
  "notes": "Lab session, bilingual",
  "created_at": "2025-12-06T10:30:00Z"
}
```

## Testing

### Prerequisites
1. Start the FastAPI server:
   ```bash
   python -m app.main
   ```

2. The server should be running at `http://localhost:8000`

### Using the Test Script
Run the provided test script:
```bash
python test_booking.py
```

This will test:
- ✅ Successful booking creation
- ❌ Unauthorized access (student role)
- ❌ Time conflict detection
- ✅ Non-conflicting booking in different time slot

### Manual Testing with curl

#### 1. Create a test JWT token
Use your existing JWT token or create one with:
- `sub`: User ID
- `role`: "lecturer"
- `email`: User email

#### 2. Create a booking
```bash
curl -X POST http://localhost:8000/rooms/401/booking \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-12-10",
    "start_time": "13:00",
    "end_time": "15:00",
    "course_name": "Data Structures",
    "notes": "Lab session"
  }'
```

## Environment Variables
Add to your `.env` file:
```env
MONGODB_URL="your-mongodb-connection-string"
DATABASE_NAME="ase"
JWT_SECRET_KEY="your-super-secret-jwt-key-change-this-in-production"
```

## Security Notes
1. Change `JWT_SECRET_KEY` in production to a strong, random key
2. JWT tokens include role-based authorization
3. Only users with `role: "lecturer"` can create bookings
4. All MongoDB queries use parameterized inputs to prevent injection

## API Documentation
Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
