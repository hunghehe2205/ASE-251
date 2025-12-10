# Feature Requirements for 4 Quality Attributes

> **Note**: Availability ✅ đã đạt được do hệ thống đã được deploy

---

## 🔐 **Nhóm 1: Authentication (Login/Logout/Register)**

### **Security (Bảo mật)**

| Feature | Mô tả | Ưu tiên |
|---------|-------|---------|
| **JWT Authentication** | Thay thế header-based auth bằng JWT access/refresh tokens | 🔴 Critical |
| **Password Policy** | Min 8 chars, require uppercase, lowercase, number, special char | 🔴 Critical |
| **Rate Limiting** | Giới hạn login attempts (5 lần/5 phút), block brute force | 🔴 Critical |
| **Email Verification** | Gửi verification email khi register, activate account | 🟡 Medium |
| **Password Reset** | Forgot password flow với reset token (expire sau 15 phút) | 🟡 Medium |
| **Session Management** | Track active sessions, logout all devices | 🟢 Low |
| **Account Lockout** | Lock account sau N failed attempts, unlock sau X phút | 🟡 Medium |
| **Remove Plaintext Password Support** | Chỉ dùng bcrypt, migrate legacy accounts | 🔴 Critical |

**Đề xuất implement:**
- JWT với access token (15 min expiry) + refresh token (7 days)
- Rate limiting với slowapi hoặc FastAPI-Limiter
- Password validation với regex pattern
- Bcrypt rounds >= 12

### **Safety (An toàn)**

| Feature | Mô tả | Ưu tiên |
|---------|-------|---------|
| **Audit Logging** | Log tất cả auth events (login success/fail, register, logout) | 🔴 Critical |
| **Input Validation** | Validate email format (RFC 5322), password strength, fullname | 🔴 Critical |
| **Error Messages** | Generic error cho invalid credentials (không reveal user exists) | 🔴 Critical |
| **Unit Tests** | Test password hashing, JWT generation, validation logic | 🔴 Critical |
| **Integration Tests** | Test full auth flows (register → verify → login → logout) | 🟡 Medium |
| **Error Handling** | Handle DB errors, JWT decode errors, expired tokens gracefully | 🔴 Critical |
| **Data Sanitization** | Strip whitespace, escape HTML trong fullname/email | 🟡 Medium |

**Đề xuất implement:**
- Logger với structured logging (JSON format)
- Pydantic validators cho email/password
- pytest tests cho auth endpoints
- Generic error: "Invalid email or password"

### **Reliability (Độ tin cậy)**

| Feature | Mô tả | Ưu tiên |
|---------|-------|---------|
| **Email Format Validation** | Regex + DNS check (optional) để verify email domain exists | 🟡 Medium |
| **Transaction Support** | Atomic operations khi create user + send verification email | 🟢 Low |
| **Idempotency** | Prevent duplicate registration với same email (race condition) | 🟡 Medium |
| **DB Indexes** | Index trên `email` field (unique) để fast lookup | 🔴 Critical |
| **Token Expiration** | JWT access token expire sau 15 min, refresh sau 7 days | 🔴 Critical |
| **Graceful Degradation** | Nếu email service down, vẫn tạo account (queue email) | 🟢 Low |
| **Connection Pooling** | Config MongoDB connection pool properly | 🟡 Medium |

**Đề xuất implement:**
- Unique index trên users.email
- JWT với exp claim
- Query timeout 5s cho auth operations
- Email validation với regex: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`

---

## 📅 **Nhóm 2: Booking Management (Create/Update/Delete)**

### **Security (Bảo mật)**

| Feature | Mô tả | Ưu tiên |
|---------|-------|---------|
| **JWT Authorization** | Verify JWT token trong header, extract user_id/role từ token | 🔴 Critical |
| **Role-Based Access Control** | Chỉ lecturer mới create/update/delete booking | 🔴 Critical |
| **Ownership Verification** | Chỉ creator mới update/delete booking của mình | 🔴 Critical |
| **Input Validation** | Validate room_id format, course_id format, notes length | 🔴 Critical |
| **SQL Injection Prevention** | Parameterized queries (đã có với MongoDB) | ✅ Done |
| **Rate Limiting** | Max 10 bookings/phút per user, prevent spam | 🟡 Medium |
| **Data Access Control** | Lecturer chỉ thấy bookings của mình, admin thấy tất cả | 🟢 Low |

**Đề xuất implement:**
- JWT middleware: extract user_id/role từ token payload
- Dependency injection cho current_user
- Role decorator: `@require_role("lecturer")`
- Ownership check: `booking.user_id == current_user.id`

### **Safety (An toàn)**

| Feature | Mô tả | Ưu tiên |
|---------|-------|---------|
| **Business Logic Validation** | start_time < end_time, booking not in past, max duration | 🔴 Critical |
| **Conflict Detection** | Check room availability BEFORE insert/update (với lock) | 🔴 Critical |
| **Audit Logging** | Log all booking operations (who, what, when, room_id) | 🔴 Critical |
| **Transaction Support** | Atomic check + insert để prevent race conditions | 🔴 Critical |
| **Unit Tests** | Test time overlap logic, validation rules | 🔴 Critical |
| **Integration Tests** | Test concurrent booking attempts, conflict scenarios | 🟡 Medium |
| **Data Validation** | Validate course_id exists (if course service available) | 🟢 Low |
| **Rollback on Error** | Rollback nếu update fails midway | 🟡 Medium |

**Đề xuất implement:**
- Pydantic validator cho time range
- MongoDB transaction cho check + insert
- Logger log mỗi booking action
- pytest test concurrent bookings
- Custom validator:
  ```python
  def validate_booking_time(date, start, end):
      # Parse to datetime
      # Check start < end
      # Check not in past
      # Check duration <= 4 hours
  ```

### **Reliability (Độ tin cậy)**

| Feature | Mô tả | Ưu tiên |
|---------|-------|---------|
| **Date/Time Format Validation** | YYYY-MM-DD, HH:MM with regex + datetime parsing | 🔴 Critical |
| **Query Timeout** | 5s timeout cho availability check, 3s cho CRUD | 🔴 Critical |
| **DB Indexes** | Compound index trên (room_id, date, start_time) | 🔴 Critical |
| **Retry Logic** | Retry failed DB operations (max 3 attempts) | 🟡 Medium |
| **Idempotency** | Prevent duplicate booking với same params (race condition) | 🟡 Medium |
| **Booking Window** | Chỉ cho phép book tối đa 30 ngày trước | 🟢 Low |
| **Time Parsing** | Convert string time to datetime object để compare chính xác | 🔴 Critical |
| **Graceful Failure** | Nếu update fails, return clear error message | 🟡 Medium |

**Đề xuất implement:**
- Pydantic `date` và `time` types (tự động validate)
- MongoDB query timeout: `max_time_ms=5000`
- Index: `db.bookings.createIndex({room_id: 1, date: 1, start_time: 1})`
- Tenacity retry decorator
- Datetime comparison thay vì string comparison:
  ```python
  from datetime import datetime, date, time

  booking_datetime = datetime.combine(
      date.fromisoformat(date_str),
      time.fromisoformat(time_str)
  )
  ```

---

## 👀 **Nhóm 3: View Schedule**

### **Security (Bảo mật)**

| Feature | Mô tả | Ưu tiên |
|---------|-------|---------|
| **JWT Authentication** | Require valid JWT token để view schedule | 🔴 Critical |
| **Data Filtering** | Student chỉ thấy own bookings, lecturer thấy own, admin thấy all | 🟡 Medium |
| **Query Parameter Validation** | Validate date range, room_id, pagination params | 🔴 Critical |
| **Rate Limiting** | Max 100 requests/phút per user cho view endpoints | 🟡 Medium |
| **PII Protection** | Không expose user password, email trong response | ✅ Done |
| **SQL Injection Prevention** | Parameterized queries cho filter params | ✅ Done |

**Đề xuất implement:**
- JWT middleware required
- Filter query based on role:
  ```python
  if role == "student":
      query = {"user_id": current_user.id}
  elif role == "lecturer":
      query = {"user_id": current_user.id}
  else:  # admin
      query = {}
  ```
- Pydantic model cho query params

### **Safety (An toàn)**

| Feature | Mô tả | Ưu tiên |
|---------|-------|---------|
| **Input Validation** | Validate date range (start_date <= end_date), valid room_id | 🔴 Critical |
| **Error Handling** | Handle invalid date format, non-existent room_id gracefully | 🔴 Critical |
| **Logging** | Log view requests (optional, for analytics) | 🟢 Low |
| **Response Sanitization** | Ensure no sensitive data leaked trong response | 🟡 Medium |
| **Pagination** | Limit results per page (max 100), prevent memory issues | 🔴 Critical |
| **Unit Tests** | Test filtering logic, date range validation | 🟡 Medium |
| **Integration Tests** | Test different user roles viewing schedules | 🟡 Medium |

**Đề xuất implement:**
- Pydantic validator cho date range
- Default pagination: 20 items/page, max 100
- Error handling cho invalid params
- Response model không include password/sensitive fields

### **Reliability (Độ tin cậy)**

| Feature | Mô tả | Ưu tiên |
|---------|-------|---------|
| **Date Range Validation** | start_date <= end_date, max range 90 days | 🔴 Critical |
| **Query Optimization** | Use indexes, limit query complexity | 🔴 Critical |
| **Query Timeout** | 10s timeout cho complex queries (multi-day range) | 🔴 Critical |
| **Caching** | Cache popular queries (today's schedule) for 5 minutes | 🟡 Medium |
| **DB Indexes** | Index trên (room_id, date), (user_id, date) | 🔴 Critical |
| **Default Values** | Default to today's schedule nếu no params provided | 🟢 Low |
| **Sorting** | Sort by date, then start_time ascending | 🟡 Medium |
| **Empty Result Handling** | Return empty array nếu no bookings found (not error) | 🟡 Medium |

**Đề xuất implement:**
- Query params với default values:
  ```python
  def get_schedule(
      room_id: Optional[str] = None,
      start_date: date = Query(default=date.today()),
      end_date: date = Query(default=date.today()),
      page: int = 1,
      limit: int = 20
  ):
      if (end_date - start_date).days > 90:
          raise HTTPException(400, "Max range 90 days")
  ```
- MongoDB indexes:
  ```python
  db.bookings.createIndex({room_id: 1, date: 1})
  db.bookings.createIndex({user_id: 1, date: 1})
  ```
- Query timeout: `max_time_ms=10000`
- Redis caching cho hot queries (optional)

---

## 📊 **Summary Table - Features by Priority**

### **Critical Features (Must Have)**

| Nhóm | Security | Safety | Reliability |
|------|----------|--------|-------------|
| **Auth** | JWT auth, Rate limiting, Password policy | Audit logging, Input validation, Error handling | DB indexes (email), Token expiration |
| **Booking** | JWT + RBAC, Ownership check | Business logic validation, Conflict detection, Transactions | Date/time validation, Query timeout, Indexes |
| **View Schedule** | JWT auth, Query validation | Pagination, Input validation | Date range validation, Query timeout, Indexes |

### **Medium Features (Should Have)**

| Nhóm | Security | Safety | Reliability |
|------|----------|--------|-------------|
| **Auth** | Email verification, Password reset, Account lockout | Unit/Integration tests, Sanitization | Idempotency, Connection pooling |
| **Booking** | Rate limiting | Audit logging, Integration tests, Rollback | Retry logic, Idempotency, Time parsing |
| **View Schedule** | Data filtering by role, Rate limiting | Response sanitization, Tests | Caching, Sorting |

### **Low Priority Features (Nice to Have)**

| Nhóm | Security | Safety | Reliability |
|------|----------|--------|-------------|
| **Auth** | Session management | - | Graceful degradation |
| **Booking** | Data access control | Course validation | Booking window |
| **View Schedule** | - | View logging | Default values, Empty handling |

---

## 🎯 **Recommended Implementation Order**

### **Phase 1: Foundation (Security + Reliability core)**
1. ✅ Move MongoDB URI to `.env`
2. Implement JWT authentication (replace header-based)
3. Add DB indexes (email, room_id+date, user_id+date)
4. Add query timeouts (5-10s)
5. Implement date/time validation với Pydantic types

### **Phase 2: Safety Core**
6. Add logging system (Python logging module)
7. Business logic validation (start < end, not in past)
8. Pagination cho view schedule
9. Error handling improvements
10. Basic unit tests

### **Phase 3: Advanced Security**
11. Rate limiting (authentication + booking endpoints)
12. Password policy enforcement
13. Remove plaintext password support
14. Ownership verification với JWT

### **Phase 4: Advanced Safety + Reliability**
15. Transaction support cho booking conflict prevention
16. Audit logging cho all operations
17. Integration tests
18. Retry logic cho DB operations
19. Caching cho view schedule

---

## 📝 **Implementation Details**

### **1. JWT Authentication Implementation**

**Access Token Structure:**
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "lecturer",
  "exp": 1234567890,
  "iat": 1234567890
}
```

**Refresh Token Structure:**
```json
{
  "sub": "user_id",
  "type": "refresh",
  "exp": 1234567890
}
```

**Implementation Steps:**
1. Install `python-jose[cryptography]`
2. Create JWT utility functions (create_access_token, verify_token)
3. Add JWT dependency for protected endpoints
4. Store refresh tokens in `refresh_tokens` collection
5. Implement token refresh endpoint

---

### **2. Database Indexes**

**Required Indexes:**
```javascript
// Users collection
db.users.createIndex({ "email": 1 }, { unique: true })
db.users.createIndex({ "user_id": 1 }, { unique: true })

// Bookings collection
db.bookings.createIndex({ "booking_id": 1 }, { unique: true })
db.bookings.createIndex({ "room_id": 1, "date": 1, "start_time": 1 })
db.bookings.createIndex({ "user_id": 1, "date": 1 })
db.bookings.createIndex({ "room_id": 1, "date": 1 })

// Refresh tokens collection
db.refresh_tokens.createIndex({ "token": 1 }, { unique: true })
db.refresh_tokens.createIndex({ "user_id": 1 })
db.refresh_tokens.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })
```

---

### **3. Logging Configuration**

**Basic Setup:**
```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

**Log Events:**
- `INFO`: Successful operations (login, register, create booking)
- `WARNING`: Invalid inputs, failed validations
- `ERROR`: Database errors, system errors
- `AUDIT`: Security events (auth failures, unauthorized access)

---

### **4. Rate Limiting Configuration**

**Using slowapi:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Apply to endpoints
@app.post("/auth/login")
@limiter.limit("5/minute")
async def login():
    pass

@app.post("/rooms/{room_id}/booking")
@limiter.limit("10/minute")
async def create_booking():
    pass
```

---

### **5. Query Timeout Configuration**

**MongoDB Client Setup:**
```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=10000,
    maxPoolSize=50,
    minPoolSize=10
)
```

**Per-Query Timeout:**
```python
result = await collection.find_one(
    {"booking_id": booking_id},
    max_time_ms=5000
)
```

---

### **6. Pydantic Date/Time Validation**

**Updated Booking Schema:**
```python
from datetime import date, time
from pydantic import BaseModel, Field, model_validator

class BookingRequest(BaseModel):
    user_id: str
    date: date  # Auto-validates YYYY-MM-DD
    start_time: time  # Auto-validates HH:MM:SS
    end_time: time
    course_id: str = Field(..., max_length=50)
    course_name: str = Field(..., max_length=100)
    notes: str | None = Field(None, max_length=500)

    @model_validator(mode='after')
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError('start_time must be before end_time')

        # Check if booking is in the past
        from datetime import datetime
        booking_datetime = datetime.combine(self.date, self.start_time)
        if booking_datetime < datetime.now():
            raise ValueError('Cannot book in the past')

        # Check max duration (e.g., 4 hours)
        duration = datetime.combine(self.date, self.end_time) - datetime.combine(self.date, self.start_time)
        if duration.seconds > 14400:  # 4 hours
            raise ValueError('Booking duration cannot exceed 4 hours')

        return self
```

---

### **7. Password Policy Validation**

**Pydantic Validator:**
```python
from pydantic import field_validator
import re

class RegisterRequest(BaseModel):
    password: str = Field(..., min_length=8, max_length=72)

    @field_validator('password')
    def validate_password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
```

---

### **8. Unit Testing Structure**

**Directory Structure:**
```
BE/tests/
├── __init__.py
├── conftest.py              # Fixtures
├── unit/
│   ├── __init__.py
│   ├── test_auth.py         # Password hashing, JWT generation
│   ├── test_validators.py   # Pydantic validators
│   └── test_booking_logic.py # Time overlap, validation
├── integration/
│   ├── __init__.py
│   ├── test_auth_endpoints.py
│   ├── test_booking_endpoints.py
│   └── test_view_schedule.py
└── conftest.py
```

**Example Test:**
```python
# tests/unit/test_validators.py
import pytest
from datetime import date, time
from app.schemas.booking import BookingRequest

def test_booking_start_before_end():
    with pytest.raises(ValueError, match="start_time must be before end_time"):
        BookingRequest(
            user_id="U001",
            date=date.today(),
            start_time=time(14, 0),
            end_time=time(12, 0),  # Invalid: end before start
            course_id="CS101",
            course_name="Intro to CS"
        )
```

---

## 🔍 **Verification Checklist**

### **Security**
- [ ] MongoDB credentials moved to `.env`
- [ ] JWT authentication implemented
- [ ] Password policy enforced
- [ ] Rate limiting on auth endpoints
- [ ] Rate limiting on booking endpoints
- [ ] RBAC implemented with JWT roles
- [ ] Ownership verification for update/delete
- [ ] CORS restricted to specific origins

### **Safety**
- [ ] Logging system configured
- [ ] Audit logging for auth events
- [ ] Audit logging for booking operations
- [ ] Business logic validation (time range)
- [ ] Error handling for all endpoints
- [ ] Unit tests written (>= 50% coverage)
- [ ] Integration tests written
- [ ] Input sanitization implemented

### **Reliability**
- [ ] Database indexes created
- [ ] Query timeouts configured
- [ ] Date/time format validation
- [ ] Pagination implemented
- [ ] Connection pooling configured
- [ ] Token expiration working
- [ ] Retry logic for critical operations
- [ ] Date range validation (max 90 days)

---

**Last Updated:** 2025-12-10
