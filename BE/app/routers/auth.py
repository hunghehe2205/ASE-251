from fastapi import APIRouter, HTTPException
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse
from app.database.db_client import get_users_collection

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user"""
    try:
        users_collection = await get_users_collection()

        # Check if username already exists
        existing_user = await users_collection.find_one({"username": request.username})
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Check if email already exists
        existing_email = await users_collection.find_one({"email": request.email})
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")

        # Insert user directly to database
        user_data = {
            "username": request.username,
            "password": request.password,
            "email": request.email,
            "role": request.role
        }

        await users_collection.insert_one(user_data)

        return AuthResponse(
            status="success",
            message="User registered successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login user"""
    try:
        users_collection = await get_users_collection()

        # Find user by username and password
        user = await users_collection.find_one({
            "username": request.username,
            "password": request.password
        })

        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        return AuthResponse(
            status="success",
            message="Login successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout", response_model=AuthResponse)
async def logout():
    """Logout user"""
    return AuthResponse(
        status="success",
        message="Logout successful"
    )
