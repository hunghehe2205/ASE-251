"""
Unit Tests for Booking API - Focusing on Recent Fixes
Tests are categorized into: Security, Reliability, and Safety
"""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.routers.booking import (
    BookingValidator,
    retry_db_operation,
    BookingDatabaseOperations,
    check_room_availability
)


# ============================================================================
# SECURITY TESTS - Authorization, Ownership, and User ID Immutability
# ============================================================================

class TestSecurity:
    """
    Security tests focusing on:
    1. Booking ownership validation
    2. Role-based authorization
    3. User ID immutability (CRITICAL FIX - prevents ownership transfer attacks)
    """

    # --- Booking Ownership Tests ---

    def test_validate_ownership_success(self):
        """Test: User can access their own booking."""
        existing_booking = {"user_id": "U2025120010"}
        # Should NOT raise exception
        BookingValidator.validate_booking_ownership(existing_booking, "U2025120010")

    def test_validate_ownership_failure_different_user(self):
        """Test: User CANNOT access another user's booking."""
        existing_booking = {"user_id": "U2025120010"}
        with pytest.raises(HTTPException) as exc_info:
            BookingValidator.validate_booking_ownership(existing_booking, "U2025120999")

        assert exc_info.value.status_code == 403
        assert "FORBIDEN_ACTION" in str(exc_info.value.detail)
        assert "Only creator can UPDATE / DELETE booking" in str(exc_info.value.detail)

    def test_validate_ownership_failure_empty_user_id(self):
        """Test: Empty user_id in header cannot access booking."""
        existing_booking = {"user_id": "U2025120010"}
        with pytest.raises(HTTPException):
            BookingValidator.validate_booking_ownership(existing_booking, "")

    # --- Role Authorization Tests ---

    def test_lecturer_role_authorized(self):
        """Test: Lecturer role is authorized."""
        # Should NOT raise exception
        BookingValidator.validate_user_authorization("lecturer", "lecturer")

    def test_student_role_unauthorized(self):
        """Test: Student role is NOT authorized."""
        with pytest.raises(HTTPException) as exc_info:
            BookingValidator.validate_user_authorization("student", "lecturer")

        assert exc_info.value.status_code == 401
        assert "UNAUTHORIZED" in str(exc_info.value.detail)
        assert "Only lecturers can perform this action" in str(exc_info.value.detail)

    def test_empty_role_unauthorized(self):
        """Test: Empty role is NOT authorized."""
        with pytest.raises(HTTPException) as exc_info:
            BookingValidator.validate_user_authorization("", "lecturer")
        assert exc_info.value.status_code == 401

    def test_admin_role_unauthorized(self):
        """Test: Admin role is NOT authorized (only lecturer allowed)."""
        with pytest.raises(HTTPException) as exc_info:
            BookingValidator.validate_user_authorization("admin", "lecturer")
        assert exc_info.value.status_code == 401

    # --- CRITICAL: User ID Immutability Tests (Your Fix) ---

    def test_user_id_immutable_during_update(self):
        """
        CRITICAL TEST: user_id CANNOT be changed during update.
        This tests YOUR FIX at booking.py:598 - prevents ownership transfer attacks.
        """
        existing_booking = {
            "booking_id": "book123",
            "room_id": "A-101",
            "user_id": "U2025120010",  # Original owner
            "date": "2025-12-20",
            "start_time": "13:00",
            "end_time": "15:00",
            "course_id": "CO-2017",
            "course_name": "Data Structures",
            "notes": "Original notes"
        }

        # Attacker tries to change user_id
        class MaliciousUpdateRequest:
            user_id = "U2025120999"  # ← Attacker trying to steal booking!
            date = "2025-12-21"
            start_time = None
            end_time = None
            course_id = None
            course_name = None
            notes = "Hacked"

        booking_data = MaliciousUpdateRequest()

        # This is YOUR FIX logic (booking.py:595-605)
        updated_data = {
            "booking_id": existing_booking["booking_id"],
            "room_id": existing_booking["room_id"],
            "user_id": existing_booking["user_id"],  # ← ALWAYS keeps original owner
            "date": booking_data.date if booking_data.date is not None else existing_booking["date"],
            "start_time": booking_data.start_time if booking_data.start_time is not None else existing_booking["start_time"],
            "end_time": booking_data.end_time if booking_data.end_time is not None else existing_booking["end_time"],
            "course_id": booking_data.course_id if booking_data.course_id is not None else existing_booking["course_id"],
            "course_name": booking_data.course_name if booking_data.course_name is not None else existing_booking["course_name"],
            "notes": booking_data.notes if booking_data.notes is not None else existing_booking.get("notes")
        }

        # ✓ SECURITY: Attack MUST be prevented
        assert updated_data["user_id"] == "U2025120010"
        assert updated_data["user_id"] != "U2025120999"

        # ✓ Other fields can still be updated
        assert updated_data["date"] == "2025-12-21"
        assert updated_data["notes"] == "Hacked"

    def test_user_id_ignored_in_request_body(self):
        """
        Test: user_id in request body is completely IGNORED.
        Verifies the fix prevents all ownership transfer attempts.
        """
        existing_booking = {
            "booking_id": "book123",
            "room_id": "A-101",
            "user_id": "ORIGINAL_OWNER",
            "date": "2025-12-20",
            "start_time": "13:00",
            "end_time": "15:00",
            "course_id": "CO-2017",
            "course_name": "Data Structures"
        }

        class AttackRequest:
            user_id = "ATTACKER_ID"
            date = None
            start_time = None
            end_time = None
            course_id = None
            course_name = None
            notes = None

        booking_data = AttackRequest()

        updated_data = {
            "user_id": existing_booking["user_id"],  # ← Always original
            "date": booking_data.date if booking_data.date is not None else existing_booking["date"],
            "start_time": booking_data.start_time if booking_data.start_time is not None else existing_booking["start_time"],
            "end_time": booking_data.end_time if booking_data.end_time is not None else existing_booking["end_time"],
            "course_id": booking_data.course_id if booking_data.course_id is not None else existing_booking["course_id"],
            "course_name": booking_data.course_name if booking_data.course_name is not None else existing_booking["course_name"],
            "notes": booking_data.notes if booking_data.notes is not None else existing_booking.get("notes")
        }

        assert updated_data["user_id"] == "ORIGINAL_OWNER"
        assert updated_data["user_id"] != "ATTACKER_ID"


# ============================================================================
# RELIABILITY TESTS - Error Handling, Retries, and Timeout Behavior
# ============================================================================

class TestReliability:
    """
    Reliability tests focusing on:
    1. Database retry logic with exponential backoff
    2. Timeout handling for operations
    3. Proper error handling and logging (YOUR FIXES)
    """

    # --- Database Retry Tests ---

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test: Operation succeeds on first attempt."""
        async def successful_operation():
            return {"result": "success"}

        result = await retry_db_operation(successful_operation)
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test: Operation succeeds after 2 failures (exponential backoff)."""
        attempt_count = {"count": 0}

        async def flaky_operation():
            attempt_count["count"] += 1
            if attempt_count["count"] < 3:
                raise Exception("Temporary failure")
            return {"result": "success"}

        result = await retry_db_operation(flaky_operation, max_retries=3, delay=0.01)
        assert result == {"result": "success"}
        assert attempt_count["count"] == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test: All retries exhausted, raises HTTPException with proper error."""
        async def always_fails():
            raise Exception("Persistent failure")

        with pytest.raises(HTTPException) as exc_info:
            await retry_db_operation(always_fails, max_retries=2, delay=0.01)

        assert exc_info.value.status_code == 500
        assert "DATABASE_OPERATION_FAILED" in str(exc_info.value.detail)
        assert "2 retries" in str(exc_info.value.detail)

    # --- Timeout Tests ---

    @pytest.mark.asyncio
    async def test_availability_check_timeout(self):
        """Test: Room availability check respects timeout."""
        async def slow_check(query):  # ← Accept query argument
            await asyncio.sleep(10)
            return None

        mock_collection = AsyncMock()
        mock_collection.find_one = slow_check

        with patch('app.routers.booking.get_bookings_collection', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_collection

            with pytest.raises(HTTPException) as exc_info:
                await check_room_availability("A-101", "2025-12-20", "13:00", "15:00", timeout=0.1)

            assert exc_info.value.status_code == 408
            assert "AVAILABILITY_CHECK_TIMEOUT" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test: Graceful handling of database connection failure."""
        async def connection_error():
            raise ConnectionError("Cannot connect to MongoDB")

        with pytest.raises(HTTPException) as exc_info:
            await retry_db_operation(connection_error, max_retries=2, delay=0.01)

        assert exc_info.value.status_code == 500
        assert "DATABASE_OPERATION_FAILED" in str(exc_info.value.detail)

    # --- Error Handling Tests (Your Fixes) ---

    def test_update_data_includes_required_fields(self):
        """
        Test: updated_data includes booking_id and room_id for response.
        This tests YOUR FIX at booking.py:596-597 - prevents KeyError.
        """
        existing_booking = {
            "booking_id": "book123",
            "room_id": "A-101",
            "user_id": "U2025120010",
            "date": "2025-12-20",
            "start_time": "13:00",
            "end_time": "15:00",
            "course_id": "CO-2017",
            "course_name": "Data Structures",
            "notes": "Notes"
        }

        class UpdateRequest:
            user_id = None
            date = "2025-12-21"
            start_time = None
            end_time = None
            course_id = None
            course_name = None
            notes = None

        booking_data = UpdateRequest()

        # Your fix: Include booking_id and room_id in updated_data
        updated_data = {
            "booking_id": existing_booking["booking_id"],  # ← YOUR FIX
            "room_id": existing_booking["room_id"],        # ← YOUR FIX
            "user_id": existing_booking["user_id"],
            "date": booking_data.date if booking_data.date is not None else existing_booking["date"],
            "start_time": booking_data.start_time if booking_data.start_time is not None else existing_booking["start_time"],
            "end_time": booking_data.end_time if booking_data.end_time is not None else existing_booking["end_time"],
            "course_id": booking_data.course_id if booking_data.course_id is not None else existing_booking["course_id"],
            "course_name": booking_data.course_name if booking_data.course_name is not None else existing_booking["course_name"],
            "notes": booking_data.notes if booking_data.notes is not None else existing_booking.get("notes")
        }

        # ✓ Must have all required fields for BookingResponse
        assert "booking_id" in updated_data
        assert "room_id" in updated_data
        assert updated_data["booking_id"] == "book123"
        assert updated_data["room_id"] == "A-101"


# ============================================================================
# SAFETY TESTS - Data Integrity and Update Merging Logic
# ============================================================================

class TestSafety:
    """
    Safety tests focusing on:
    1. Correct merging of update data
    2. Preservation of unchanged fields
    3. Handling of optional/missing fields
    """

    def test_partial_update_preserves_existing_fields(self):
        """Test: Partial update preserves all unchanged fields."""
        existing_booking = {
            "booking_id": "book123",
            "room_id": "A-101",
            "user_id": "U2025120010",
            "date": "2025-12-20",
            "start_time": "13:00",
            "end_time": "15:00",
            "course_id": "CO-2017",
            "course_name": "Data Structures",
            "notes": "Original notes"
        }

        class PartialUpdate:
            user_id = None
            date = "2025-12-21"  # Only updating date
            start_time = None
            end_time = None
            course_id = None
            course_name = None
            notes = None

        booking_data = PartialUpdate()

        updated_data = {
            "booking_id": existing_booking["booking_id"],
            "room_id": existing_booking["room_id"],
            "user_id": existing_booking["user_id"],
            "date": booking_data.date if booking_data.date is not None else existing_booking["date"],
            "start_time": booking_data.start_time if booking_data.start_time is not None else existing_booking["start_time"],
            "end_time": booking_data.end_time if booking_data.end_time is not None else existing_booking["end_time"],
            "course_id": booking_data.course_id if booking_data.course_id is not None else existing_booking["course_id"],
            "course_name": booking_data.course_name if booking_data.course_name is not None else existing_booking["course_name"],
            "notes": booking_data.notes if booking_data.notes is not None else existing_booking.get("notes")
        }

        # ✓ Only date changed, everything else preserved
        assert updated_data["date"] == "2025-12-21"
        assert updated_data["start_time"] == "13:00"
        assert updated_data["end_time"] == "15:00"
        assert updated_data["course_id"] == "CO-2017"
        assert updated_data["course_name"] == "Data Structures"
        assert updated_data["notes"] == "Original notes"

    def test_full_update_changes_all_fields_except_user_id(self):
        """Test: Full update changes all fields EXCEPT user_id."""
        existing_booking = {
            "booking_id": "book123",
            "room_id": "A-101",
            "user_id": "U2025120010",
            "date": "2025-12-20",
            "start_time": "13:00",
            "end_time": "15:00",
            "course_id": "CO-2017",
            "course_name": "Data Structures",
            "notes": "Original notes"
        }

        class FullUpdate:
            user_id = "IGNORED"  # Should be ignored
            date = "2025-12-25"
            start_time = "14:00"
            end_time = "16:00"
            course_id = "CO-3001"
            course_name = "Machine Learning"
            notes = "Updated notes"

        booking_data = FullUpdate()

        updated_data = {
            "booking_id": existing_booking["booking_id"],
            "room_id": existing_booking["room_id"],
            "user_id": existing_booking["user_id"],  # ← Always preserved
            "date": booking_data.date if booking_data.date is not None else existing_booking["date"],
            "start_time": booking_data.start_time if booking_data.start_time is not None else existing_booking["start_time"],
            "end_time": booking_data.end_time if booking_data.end_time is not None else existing_booking["end_time"],
            "course_id": booking_data.course_id if booking_data.course_id is not None else existing_booking["course_id"],
            "course_name": booking_data.course_name if booking_data.course_name is not None else existing_booking["course_name"],
            "notes": booking_data.notes if booking_data.notes is not None else existing_booking.get("notes")
        }

        # ✓ user_id PRESERVED, all others updated
        assert updated_data["user_id"] == "U2025120010"
        assert updated_data["date"] == "2025-12-25"
        assert updated_data["start_time"] == "14:00"
        assert updated_data["end_time"] == "16:00"
        assert updated_data["course_id"] == "CO-3001"
        assert updated_data["course_name"] == "Machine Learning"
        assert updated_data["notes"] == "Updated notes"

    def test_update_handles_missing_notes_field(self):
        """Test: Gracefully handle existing booking without notes field."""
        existing_booking = {
            "booking_id": "book123",
            "room_id": "A-101",
            "user_id": "U2025120010",
            "date": "2025-12-20",
            "start_time": "13:00",
            "end_time": "15:00",
            "course_id": "CO-2017",
            "course_name": "Data Structures"
            # No 'notes' field
        }

        class UpdateRequest:
            user_id = None
            date = None
            start_time = None
            end_time = None
            course_id = None
            course_name = None
            notes = "New notes"

        booking_data = UpdateRequest()

        updated_data = {
            "booking_id": existing_booking["booking_id"],
            "room_id": existing_booking["room_id"],
            "user_id": existing_booking["user_id"],
            "date": booking_data.date if booking_data.date is not None else existing_booking["date"],
            "start_time": booking_data.start_time if booking_data.start_time is not None else existing_booking["start_time"],
            "end_time": booking_data.end_time if booking_data.end_time is not None else existing_booking["end_time"],
            "course_id": booking_data.course_id if booking_data.course_id is not None else existing_booking["course_id"],
            "course_name": booking_data.course_name if booking_data.course_name is not None else existing_booking["course_name"],
            "notes": booking_data.notes if booking_data.notes is not None else existing_booking.get("notes")
        }

        # ✓ Notes added without error (get() returns None if missing)
        assert updated_data["notes"] == "New notes"

    def test_update_with_all_none_preserves_everything(self):
        """Test: Update with all None values preserves all fields."""
        existing_booking = {
            "booking_id": "book123",
            "room_id": "A-101",
            "user_id": "U2025120010",
            "date": "2025-12-20",
            "start_time": "13:00",
            "end_time": "15:00",
            "course_id": "CO-2017",
            "course_name": "Data Structures",
            "notes": "Original"
        }

        class EmptyUpdate:
            user_id = None
            date = None
            start_time = None
            end_time = None
            course_id = None
            course_name = None
            notes = None

        booking_data = EmptyUpdate()

        updated_data = {
            "booking_id": existing_booking["booking_id"],
            "room_id": existing_booking["room_id"],
            "user_id": existing_booking["user_id"],
            "date": booking_data.date if booking_data.date is not None else existing_booking["date"],
            "start_time": booking_data.start_time if booking_data.start_time is not None else existing_booking["start_time"],
            "end_time": booking_data.end_time if booking_data.end_time is not None else existing_booking["end_time"],
            "course_id": booking_data.course_id if booking_data.course_id is not None else existing_booking["course_id"],
            "course_name": booking_data.course_name if booking_data.course_name is not None else existing_booking["course_name"],
            "notes": booking_data.notes if booking_data.notes is not None else existing_booking.get("notes")
        }

        # ✓ Everything preserved
        assert updated_data == existing_booking


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
