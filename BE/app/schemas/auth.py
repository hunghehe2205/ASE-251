from pydantic import BaseModel, EmailStr
from typing import Literal


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: EmailStr
    role: Literal["student", "lecturer"]


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    status: str
    message: str
