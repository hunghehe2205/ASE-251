import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from passlib.context import CryptContext

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    RegisterResponse,
    RegisterResponseData,
    RegisterResponseMeta,
)
from app.database.db_client import get_users_collection

router = APIRouter(prefix="/auth", tags=["Authentication"])

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False,  
)

_MAX_PASSWORD_BYTES = 72


def _hash_password(password: str) -> str:
    if password is None:
        raise HTTPException(status_code=400, detail="Password is required")
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at most {_MAX_PASSWORD_BYTES} bytes",
        )
    return _pwd_context.hash(password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


async def _generate_user_id(users_collection) -> str:
    """Generate user_id like UYYYYMM0001, incrementing per month."""
    now = datetime.utcnow()
    prefix = f"U{now.year}{now.month:02d}"
    count = await users_collection.count_documents({"user_id": {"$regex": f"^{prefix}"}})
    sequence = count + 1
    return f"{prefix}{sequence:04d}"


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
)
async def register(request: RegisterRequest):
    """Register a new user with validation and unique email."""
    users_collection = await get_users_collection()

    if not request.fullname or not request.email or not request.password:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "fullname, email and password are required",
                }
            },
        )

    if not _EMAIL_REGEX.match(request.email):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_EMAIL_FORMAT",
                    "message": "Email format is invalid",
                }
            },
        )

    role = request.role or ""
    if role not in ("lecturer", "student"):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "role must be either 'lecturer' or 'student'",
                }
            },
        )

    existing_email = await users_collection.find_one({"email": request.email})
    if existing_email:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "EMAIL_ALREADY_EXISTS",
                    "message": "User with this email already registered",
                }
            },
        )

    try:
        user_id = await _generate_user_id(users_collection)
        user_doc = {
            "user_id": user_id,
            "fullname": request.fullname,
            "email": request.email,
            "password": _hash_password(request.password),
            "role": role,
            "created_at": datetime.utcnow(),
        }
        await users_collection.insert_one(user_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    response = RegisterResponse(
        data=RegisterResponseData(
            user_id=user_id,
            fullname=request.fullname,
            email=request.email,
            role=role,
        ),
        meta=RegisterResponseMeta(message="Registration successful"),
    )
    return response


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login user with email/password and return role."""
    users_collection = await get_users_collection()

    # Missing input
    if not request.email or not request.password:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Missing email or password",
                }
            },
        )

    # Find user by email
    user = await users_collection.find_one({"email": request.email})

    # Wrong credentials (email not found)
    if not user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Email or password is incorrect",
                }
            },
        )

    # Blacklist check (optional flag in DB)
    if user.get("is_blacklisted"):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "code": "FORBIDDEN_ROLE",
                    "message": "You are not allowed to access this system",
                }
            },
        )

    stored_password = user.get("password", "")
    is_hash = isinstance(stored_password, str) and stored_password.startswith(("$2a$", "$2b$", "$2y$"))

    # Verify password: support both bcrypt hash and legacy plaintext
    if is_hash:
        valid = _verify_password(request.password, stored_password)
    else:
        valid = request.password == stored_password

    if not valid:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Email or password is incorrect",
                }
            },
        )

    # Success: return only role
    return JSONResponse(
        status_code=status.HTTP_200_OK, 
        content={
            "role": user.get("role", ""),
            "user_id" : user.get("user_id",""),
            "fullname": user.get("fullname", ""),
            "email": user.get("email", "")
            }
        )


@router.post("/logout", response_model=AuthResponse)
async def logout():
    """Logout user"""
    return AuthResponse(status="success", message="Logout successful")
