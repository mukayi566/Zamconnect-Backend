from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional, List
from datetime import date
import re
from app.models.enums import CitizenStatus

ZAMBIAN_PROVINCES = [
    "Lusaka", "Copperbelt", "Eastern", "Southern", "Northern",
    "Western", "Luapula", "Central", "North-Western", "Muchinga"
]

class CitizenCreateRequest(BaseModel):
    registration_type: Optional[str] = "full"  # "basic" or "full"
    nrc_number: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    province: str
    district: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    guardian_id: Optional[str] = None
    # Document URLs
    nrc_url: Optional[str] = None
    passport_url: Optional[str] = None
    birth_cert_url: Optional[str] = None
    selfie_url: Optional[str] = None
    photo_url: Optional[str] = None
    signature_url: Optional[str] = None
    nrc_back_url: Optional[str] = None
    biometrics_enabled: Optional[bool] = False

    @field_validator("nrc_number")
    @classmethod
    def validate_nrc(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^\d{6}/\d{2}/\d$", v):
            raise ValueError("NRC must match format 000000/00/0")
        return v

    @field_validator("province")
    @classmethod
    def validate_province(cls, v: str) -> str:
        if v not in ZAMBIAN_PROVINCES:
            raise ValueError(f"Must be one of: {', '.join(ZAMBIAN_PROVINCES)}")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^\+260\d{9}$", v):
            raise ValueError("Phone must be in format +260XXXXXXXXX")
        return v

class CitizenStatusUpdateRequest(BaseModel):
    status: CitizenStatus
    reason: Optional[str] = None

class CitizenUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    photo_url: Optional[str] = None
    selfie_url: Optional[str] = None
    signature_url: Optional[str] = None
    nrc_url: Optional[str] = None
    nrc_back_url: Optional[str] = None
    passport_url: Optional[str] = None
    birth_cert_url: Optional[str] = None

class CitizenResponse(BaseModel):
    id: str
    nrc_number: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    province: str
    district: Optional[str]
    status: str
    qr_payload: Optional[str]
    guardian_id: Optional[str]
    created_at: str
    updated_at: str
    # Document URLs
    nrc_url: Optional[str] = None
    passport_url: Optional[str] = None
    birth_cert_url: Optional[str] = None
    selfie_url: Optional[str] = None
    photo_url: Optional[str] = None
    signature_url: Optional[str] = None
    nrc_back_url: Optional[str] = None

class PaginatedCitizenResponse(BaseModel):
    success: bool
    message: str
    data: List[CitizenResponse]
    meta: dict
