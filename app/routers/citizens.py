"""
Citizens Router — ZamID Connect

Includes v2 security upgrades:
  - /citizens/{id}/qr-token  → issues a short-lived JWT QR token (60s, one-time)
  - QR generation no longer stores static payload in DB — tokens are always fresh
  - Audit logging on every state-changing action
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import Optional

from app.schemas.citizen import CitizenCreateRequest, CitizenStatusUpdateRequest, CitizenUpdateRequest
from app.config.supabase import supabase
from app.middleware.auth import role_required, get_current_user
from app.models.enums import UserRole, CitizenStatus, AuditAction
from app.utils.response import api_response
from app.services.qr_service import generate_qr_token, generate_qr_payload
from app.services.audit_service import log_audit
import uuid

router = APIRouter(prefix="/citizens", tags=["Citizens"])


# ---------------------------------------------------------------------------
# List citizens (admin / registrar)
# ---------------------------------------------------------------------------

@router.get("")
async def get_citizens(
    page: int = 1,
    limit: int = 20,
    status: str = "all",
    province: str = "all",
    search: str = "",
    current_user: dict = Depends(get_current_user),
):
    query = supabase.table("citizens").select("*", count="exact")

    if status != "all":
        query = query.eq("status", status)
    if province != "all":
        query = query.eq("province", province)
    if search:
        query = query.or_(
            f"nrc_number.ilike.%{search}%,first_name.ilike.%{search}%,last_name.ilike.%{search}%"
        )

    start = (page - 1) * limit
    end = start + limit - 1
    res = query.range(start, end).order("created_at", desc=True).execute()

    total = res.count
    pages = (total + limit - 1) // limit

    return api_response(
        success=True,
        message="Citizens fetched",
        data=res.data,
        meta={"total": total, "page": page, "limit": limit, "pages": pages},
    )


@router.get("/{id}")
async def get_citizen_by_id(
    id: str,
    current_user: dict = Depends(get_current_user),
):
    res = supabase.table("citizens").select("*").eq("id", id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Citizen not found")
    
    return api_response(success=True, message="Citizen fetched", data=res.data[0])


# ---------------------------------------------------------------------------
# Register a citizen (admin / registrar)
# ---------------------------------------------------------------------------

@router.post("")
async def register_citizen(
    request: CitizenCreateRequest,
    current_user: dict = Depends(role_required([UserRole.ADMIN, UserRole.REGISTRAR])),
):
    # Only check for duplicate NRC when one is provided (full registration)
    if request.nrc_number:
        existing = supabase.table("citizens").select("id").eq("nrc_number", request.nrc_number).execute()
        if existing.data:
            raise HTTPException(status_code=409, detail="NRC number already registered")

    citizen_id = str(uuid.uuid4())
    citizen_data = request.model_dump()
    citizen_data["id"] = citizen_id
    citizen_data["status"] = CitizenStatus.PENDING
    citizen_data["date_of_birth"] = citizen_data["date_of_birth"].isoformat()

    # No static QR payload stored — tokens are generated on-demand per scan
    res = supabase.table("citizens").insert(citizen_data).execute()

    await log_audit(
        action=AuditAction.REGISTER_CITIZEN,
        actor_id=current_user["sub"],
        actor_email=current_user["email"],
        target_id=citizen_id,
        target_type="citizen",
        details={
            "registration_type": request.registration_type,
            "nrc_number": request.nrc_number,
            "province": request.province,
        },
    )

    return api_response(success=True, message="Citizen registered", data=res.data[0])


# ---------------------------------------------------------------------------
# Update citizen status (admin only)
# ---------------------------------------------------------------------------

@router.patch("/{id}/status")
async def update_status(
    id: str,
    request: CitizenStatusUpdateRequest,
    current_user: dict = Depends(role_required([UserRole.ADMIN])),
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
        details={"new_status": request.status, "reason": request.reason},
    )

    return api_response(success=True, message="Status updated", data=res.data[0])


# ---------------------------------------------------------------------------
# My profile (authenticated citizen)
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    res = supabase.table("citizens").select("*").eq("id", current_user["sub"]).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Citizen profile not found")
    return api_response(success=True, message="Profile fetched", data=res.data[0])


@router.get("/dependents")
async def get_my_dependents(current_user: dict = Depends(get_current_user)):
    res = supabase.table("citizens").select("*").eq("guardian_id", current_user["sub"]).execute()
    return api_response(success=True, message="Dependents fetched", data=res.data)


# ---------------------------------------------------------------------------
# QR Token Generation (v2 — one-time, 60-second JWT)
# ---------------------------------------------------------------------------

@router.get("/{id}/qr-token")
async def generate_citizen_qr_token(
    id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Issue a fresh signed JWT QR token for the citizen identified by `id`.

    Security:
      - Token expires in 60 seconds
      - Contains a unique jti (cannot be replayed after scan)
      - Does NOT contain NRC number or sensitive data — only citizen UUID
      - Citizen must own this profile or be an admin/registrar

    The mobile app calls this endpoint on every "Show QR" action.
    The QR code is rendered from the returned token string.
    """
    # Authorisation check: citizen can only request their own QR
    if current_user["sub"] != id and current_user.get("role") not in [
        UserRole.ADMIN, UserRole.REGISTRAR
    ]:
        raise HTTPException(status_code=403, detail="You may only request your own QR token")

    res = supabase.table("citizens").select("id, first_name, last_name, status").eq("id", id).execute()

    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Citizen not found")

    citizen = res.data[0]

    if citizen["status"] != "active":
        raise HTTPException(
            status_code=403,
            detail=f"QR tokens can only be issued for active citizens. Current status: {citizen['status']}",
        )

    token = generate_qr_token(citizen)

    await log_audit(
        action=AuditAction.REGENERATE_QR,
        actor_id=current_user["sub"],
        actor_email=current_user.get("email", ""),
        target_id=id,
        target_type="citizen",
        details={"method": "jwt_v2"},
    )

    return api_response(
        success=True,
        message="QR token issued — valid for 60 seconds",
        data={
            "qr_token": token,
            "expires_in": 60,
            "algorithm": "HS256",
            "version": "2.0",
        },
    )


# ---------------------------------------------------------------------------
# Legacy QR payload endpoint — kept for backward compat, deprecated
# ---------------------------------------------------------------------------

@router.get("/{id}/qr")
async def get_citizen_qr_legacy(
    id: str,
    current_user: dict = Depends(get_current_user),
):
    """[DEPRECATED] Returns HMAC-signed JSON QR payload. Use /qr-token instead."""
    res = supabase.table("citizens").select("*").eq("id", id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="Citizen not found")

    citizen = res.data[0]
    qr = generate_qr_payload(citizen)

    return api_response(
        success=True,
        message="[Deprecated] Use /qr-token for secure one-time tokens",
        data={"qr_payload": qr, "deprecated": True},
    )
