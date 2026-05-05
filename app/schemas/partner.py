from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class PartnerBase(BaseModel):
    organisation_name: str
    organisation_type: str
    contact_name: str
    contact_email: EmailStr
    contact_phone: str
    purpose: str
    website: Optional[str] = None
    zicta_license: Optional[str] = None
    requested_fields: List[str]

class PartnerCreate(PartnerBase):
    pass

class PartnerUpdate(BaseModel):
    status: str # 'pending', 'approved', 'rejected'

class Partner(PartnerBase):
    id: str
    status: str
    sandbox_api_key: str
    production_api_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
