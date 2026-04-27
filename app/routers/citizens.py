from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.schemas.citizen import CitizenCreateRequest, CitizenStatusUpdateRequest, CitizenUpdateRequest
from app.config.supabase import supabase
from app.middleware.auth import role_required, get_current_user
from app.models.enums import UserRole, CitizenStatus, AuditAction
from app.utils.response import api_response
from app.services.qr_service import generate_qr_payload
from app.services.audit_service import log_audit
import uuid

router = APIRouter(prefix="/citizens", tags=["Citizens"])

@router.get("")
async def get_citizens(
    page: int = 1,
    limit: int = 20,
    status: str = "all",
    province: str = "all",
    search: str = "",
    current_user: dict = Depends(get_current_user)
):
    query = supabase.table("citizens").select("*", count="exact")
    
    if status != "all":
        query = query.eq("status", status)
    if province != "all":
        query = query.eq("province", province)
    if search:
        query = query.or_(f"nrc_number.ilike.%{search}%,first_name.ilike.%{search}%,last_name.ilike.%{search}%")
    
    # Pagination
    start = (page - 1) * limit
    end = start + limit - 1
    
    res = query.range(start, end).order("created_at", desc=True).execute()
    
    total = res.count
    pages = (total + limit - 1) // limit
    
    return api_response(
        success=True,
        message="Citizens fetched",
        data=res.data,
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages
        }
    )

@router.post("")
async def register_citizen(
    request: CitizenCreateRequest,
    current_user: dict = Depends(role_required([UserRole.ADMIN, UserRole.REGISTRAR]))
):
    # Check if exists
    existing = supabase.table("citizens").select("id").eq("nrc_number", request.nrc_number).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="NRC number already registered")
    
    citizen_id = str(uuid.uuid4())
    
    citizen_data = request.model_dump()
    citizen_data["id"] = citizen_id
    citizen_data["status"] = CitizenStatus.PENDING
    
    # Generate QR payload
    qr_payload = generate_qr_payload(citizen_data)
    citizen_data["qr_payload"] = qr_payload
    # Pydantic date to string
    citizen_data["date_of_birth"] = citizen_data["date_of_birth"].isoformat()

    res = supabase.table("citizens").insert(citizen_data).execute()
    
    await log_audit(
        action=AuditAction.REGISTER_CITIZEN,
        actor_id=current_user["sub"],
        actor_email=current_user["email"],
        target_id=citizen_id,
        target_type="citizen",
        details=citizen_data
    )
    
    return api_response(success=True, message="Citizen registered", data=res.data[0])

@router.patch("/{id}/status")
async def update_status(
    id: str,
    request: CitizenStatusUpdateRequest,
    current_user: dict = Depends(role_required([UserRole.ADMIN]))
):
    res = supabase.table("citizens").update({"status": request.status}).eq("id", id).execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Citizen not found")
        
    await log_audit(
        action=AuditAction.CHANGE_STATUS,
        actor_id=current_user["sub"],
        actor_email=current_user["email"],
        target_id=id,
        target_type="citizen",
        details={"new_status": request.status, "reason": request.reason}
    )
    
    return api_response(success=True, message="Status updated", data=res.data[0])

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    res = supabase.table("citizens").select("*").eq("id", current_user["sub"]).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Citizen profile not found")
    return api_response(success=True, message="Profile fetched", data=res.data)

@router.get("/dependents")
async def get_my_dependents(current_user: dict = Depends(get_current_user)):
    res = supabase.table("citizens").select("*").eq("guardian_id", current_user["sub"]).execute()
    return api_response(success=True, message="Dependents fetched", data=res.data)


