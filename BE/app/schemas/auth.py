from typing import Literal, Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    fullname: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[Literal["lecturer", "student"]] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    status: str
    message: str


class LoginResponse(BaseModel):
    status: str
    message: str
    role: str
    user_id: str
    fullname: str
    email: str


class RegisterResponseData(BaseModel):
    user_id: str
    fullname: str
    email: str
    role: Literal["lecturer", "student"]


class RegisterResponseMeta(BaseModel):
    message: str


class RegisterResponse(BaseModel):
    data: RegisterResponseData
    meta: RegisterResponseMeta
