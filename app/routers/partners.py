from fastapi import APIRouter, Depends, HTTPException, status
from app.config.supabase import supabase
from app.utils.response import api_response
from app.middleware.auth import role_required
from app.models.enums import UserRole
from app.schemas.partner import PartnerCreate, PartnerUpdate
import uuid
from datetime import datetime

router = APIRouter(prefix="/partner", tags=["Partners"])

@router.post("/register")
async def register_partner(partner: PartnerCreate):
    # Check if email already exists
    existing = supabase.table("partners").select("*").eq("contact_email", partner.contact_email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Organisation with this email already applied")

    sandbox_key = f"sbx_{uuid.uuid4().hex}"
    
    partner_data = partner.model_dump()
    partner_data["status"] = "pending"
    partner_data["sandbox_api_key"] = sandbox_key
    partner_data["created_at"] = datetime.utcnow().isoformat()

    result = supabase.table("partners").insert(partner_data).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to register partner")

    return api_response(
        success=True,
        message="Application submitted successfully",
        data={"sandbox_api_key": sandbox_key}
    )

@router.get("/")
async def get_partners(current_user: dict = Depends(role_required([UserRole.ADMIN]))):
    result = supabase.table("partners").select("*").order("created_at", desc=True).execute()
    return api_response(
        success=True,
        message="Partners fetched",
        data=result.data
    )

@router.post("/{partner_id}/status")
async def update_partner_status(
    partner_id: str, 
    update: PartnerUpdate,
    current_user: dict = Depends(role_required([UserRole.ADMIN]))
):
    # If approving, generate production API key
    update_data = {"status": update.status}
    if update.status == "approved":
        update_data["production_api_key"] = f"live_{uuid.uuid4().hex}"

    result = supabase.table("partners").update(update_data).eq("id", partner_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Partner not found")

    return api_response(
        success=True,
        message=f"Partner {update.status}",
        data=result.data[0]
    )

@router.post("/{partner_id}/regenerate-key")
async def regenerate_partner_key(
    partner_id: str,
    key_type: str, # "sandbox" or "production"
    current_user: dict = Depends(role_required([UserRole.ADMIN]))
):
    new_key = f"{'sbx' if key_type == 'sandbox' else 'live'}_{uuid.uuid4().hex}"
    field = "sandbox_api_key" if key_type == "sandbox" else "production_api_key"
    
    result = supabase.table("partners").update({field: new_key}).eq("id", partner_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Partner not found")

    return api_response(
        success=True,
        message=f"{key_type.capitalize()} key regenerated",
        data={field: new_key}
    )
