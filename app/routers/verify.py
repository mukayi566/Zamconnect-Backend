from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
from app.config.supabase import supabase
from app.services.qr_service import verify_qr_payload
from app.utils.response import api_response
from app.middleware.auth import get_current_user
from app.services.audit_service import log_audit
from app.models.enums import AuditAction

router = APIRouter(prefix="/verify", tags=["Verification"])

class NRCVerifyRequest(BaseModel):
    nrc_number: str
    organization: Optional[str] = None

class QRVerifyRequest(BaseModel):
    qr_payload: str
    organization: Optional[str] = None

@router.post("/nrc")
async def verify_nrc(request: NRCVerifyRequest, current_user: dict = Depends(get_current_user)):
    res = supabase.table("citizens").select("*").eq("nrc_number", request.nrc_number).execute()
    
    if not res.data:
        return api_response(success=False, message="Identity not found", code="CITIZEN_NOT_FOUND")
    
    citizen = res.data[0]
    
    await log_audit(
        action=AuditAction.VERIFY_NRC,
        actor_id=current_user["sub"],
        actor_email=current_user["email"],
        target_id=citizen["id"],
        target_type="citizen",
        details={"organization": request.organization}
    )
    
    return api_response(success=True, message="Identity verified", data={"result": "verified", "citizen": citizen})

@router.post("/qr")
async def verify_qr(request: QRVerifyRequest, current_user: dict = Depends(get_current_user)):
    valid, payload = verify_qr_payload(request.qr_payload)
    
    if not valid:
        return api_response(success=False, message="QR payload invalid or tampered", code="QR_TAMPERED")
    
    # Check if citizen still exists and is active in DB
    res = supabase.table("citizens").select("*").eq("id", payload["citizen_id"]).single().execute()
    
    if not res.data:
        return api_response(success=False, message="Citizen record not found", code="CITIZEN_NOT_FOUND")
        
    citizen = res.data
    
    await log_audit(
        action=AuditAction.VERIFY_QR,
        actor_id=current_user["sub"],
        actor_email=current_user["email"],
        target_id=citizen["id"],
        target_type="citizen",
        details={"organization": request.organization}
    )
    
    return api_response(success=True, message="Identity verified", data={"result": "verified", "citizen": citizen})

@router.get("/logs")
async def get_verification_logs(
    page: int = 1,
    limit: int = 20,
    result: str = "all",
    search: str = "",
    current_user: dict = Depends(get_current_user)
):
    query = supabase.table("verification_logs").select("*, citizens(*)", count="exact")
    
    if result != "all":
        query = query.eq("result", result)
    if search:
        query = query.or_(f"organization.ilike.%{search}%,ip_address.ilike.%{search}%")
        
    start = (page - 1) * limit
    end = start + limit - 1
    
    res = query.range(start, end).order("created_at", desc=True).execute()
    
    return api_response(
        success=True,
        message="Logs fetched",
        data=res.data,
        meta={"total": res.count, "page": page, "limit": limit}
    )

