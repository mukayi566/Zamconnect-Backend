from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict, Any

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class RefreshRequest(BaseModel):
    refresh_token: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    registration_type: Optional[str] = "full"
    full_name: Optional[str] = None
    nrc: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = "male"
    phone: Optional[str] = None
    address: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None

    @field_validator("nrc")
    @classmethod
    def validate_nrc(cls, v: Optional[str]) -> Optional[str]:
        import re
        if v is not None and not re.match(r"^\d{6}/\d{2}/\d$", v):
            raise ValueError("NRC must match format 000000/00/0")
        return v
    # Document URLs
    nrc_url: Optional[str] = None
    passport_url: Optional[str] = None
    birth_cert_url: Optional[str] = None
    selfie_url: Optional[str] = None
    photo_url: Optional[str] = None
    signature_url: Optional[str] = None
    nrc_back_url: Optional[str] = None
    biometrics_enabled: Optional[bool] = False
    guardian_id: Optional[str] = None

class AgeVerificationResponse(BaseModel):
    is_eligible: bool
    age: int
    message: str

class DependentCreateRequest(BaseModel):
    full_name: str
    date_of_birth: str
    gender: str = "male"
    birth_cert_url: Optional[str] = None
    nrc: Optional[str] = None
    # Copy some fields from parent if needed, but let's keep it simple

