from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.enums import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RefreshRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    status: str
