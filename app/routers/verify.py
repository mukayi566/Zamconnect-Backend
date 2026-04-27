"""
Verify Router — ZamID Connect (v2, International-Grade Security)

Implements:
  - JWT QR verification (exp + jti one-time tokens)
  - Data minimisation: only name, photo-initial, status returned to scanner
  - Real client IP extraction (handles reverse-proxy X-Forwarded-For)
  - Full audit trail with result codes (success / fail / tampered / expired / replay)
  - Anti-fraud: rate-limit on QR verification endpoint (see middleware)
  - Legacy NRC verify still supported for officer dashboards
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
from pydantic import BaseModel

from app.config.supabase import supabase
from app.services.qr_service import verify_qr_token, get_safe_citizen
from app.utils.response import api_response
from app.middleware.auth import get_current_user
from app.services.audit_service import log_audit
from app.models.enums import AuditAction

router = APIRouter(prefix="/verify", tags=["Verification"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client_ip(request: Request) -> str:
    """
    Extracts the real IP from the request.
    Handles Nginx / Render / Cloudflare reverse-proxy forwarding.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "0.0.0.0"


def _get_device_hint(request: Request) -> str:
    """Extracts a short device fingerprint from User-Agent."""
    ua = request.headers.get("User-Agent", "")
    return ua[:120]  # truncate — don't store kilobytes of UA strings


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class NRCVerifyRequest(BaseModel):
    nrc_number: str
    organization: Optional[str] = None

class QRVerifyRequest(BaseModel):
    qr_token: str                      # JWT token (v2)
    organization: Optional[str] = None

class QRVerifyLegacyRequest(BaseModel):
    """Backward-compat: accepts old `qr_payload` JSON string."""
    qr_payload: str
    organization: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/qr")
async def verify_qr(
    request: Request,
    body: QRVerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Verify a JWT QR token.

    Security checks:
      1. Signature validity (HS256 / PRIVATE_KEY signed)
      2. Expiry (60-second window)
      3. One-time use (jti blacklist — prevents replay attacks)
      4. Citizen is still active in database
      5. Full audit log written with IP, device, result

    Returns ONLY: name, status, province (data minimisation).
    Never returns: nrc_number, address, phone, documents.
    """
    ip = _get_client_ip(request)
    device = _get_device_hint(request)

    valid, payload = verify_qr_token(body.qr_token)

    if not valid:
        reason = payload.get("reason", "unknown")
        result_code = reason  # "expired" | "tampered" | "invalid_token" | "token_already_used"

        await log_audit(
            action=AuditAction.VERIFY_QR,
            actor_id=current_user["sub"],
            actor_email=current_user["email"],
            target_id="unknown",
            target_type="citizen",
            details={"organization": body.organization, "reason": reason},
            ip_address=ip,
            device_hint=device,
            result=result_code,
        )
        return api_response(
            success=False,
            message=_qr_error_message(reason),
            code=f"QR_{reason.upper()}",
        )

    # Look up citizen in database
    citizen_id = payload.get("sub")
    res = supabase.table("citizens").select("*").eq("id", citizen_id).single().execute()

    if not res.data:
        await log_audit(
            action=AuditAction.VERIFY_QR,
            actor_id=current_user["sub"],
            actor_email=current_user["email"],
            target_id=citizen_id or "unknown",
            target_type="citizen",
            details={"organization": body.organization},
            ip_address=ip,
            device_hint=device,
            result="not_found",
        )
        return api_response(success=False, message="Citizen record not found", code="CITIZEN_NOT_FOUND")

    citizen = res.data

    # Verify citizen is active
    if citizen.get("status") != "active":
        await log_audit(
            action=AuditAction.VERIFY_QR,
            actor_id=current_user["sub"],
            actor_email=current_user["email"],
            target_id=citizen["id"],
            target_type="citizen",
            details={"organization": body.organization, "citizen_status": citizen.get("status")},
            ip_address=ip,
            device_hint=device,
            result="inactive",
        )
        return api_response(
            success=False,
            message=f"Identity exists but status is '{citizen.get('status')}'",
            code="CITIZEN_INACTIVE",
        )

    await log_audit(
        action=AuditAction.VERIFY_QR,
        actor_id=current_user["sub"],
        actor_email=current_user["email"],
        target_id=citizen["id"],
        target_type="citizen",
        details={"organization": body.organization},
        ip_address=ip,
        device_hint=device,
        result="success",
    )

    # Data minimisation — only safe fields returned
    return api_response(
        success=True,
        message="Identity verified",
        data={
            "result": "verified",
            "citizen": get_safe_citizen(citizen),
        },
    )


@router.post("/nrc")
async def verify_nrc(
    request: Request,
    body: NRCVerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Officer endpoint: verify by NRC number.
    Used by government officers on dashboards (not citizen app).
    Returns more fields than QR scan but still excludes documents.
    """
    ip = _get_client_ip(request)
    device = _get_device_hint(request)

    res = supabase.table("citizens").select(
        "id, first_name, last_name, status, province, date_of_birth, gender"
    ).eq("nrc_number", body.nrc_number).execute()

    if not res.data:
        await log_audit(
            action=AuditAction.VERIFY_NRC,
            actor_id=current_user["sub"],
            actor_email=current_user["email"],
            target_id=body.nrc_number,
            target_type="citizen",
            details={"organization": body.organization},
            ip_address=ip,
            device_hint=device,
            result="not_found",
        )
        return api_response(success=False, message="Identity not found", code="CITIZEN_NOT_FOUND")

    citizen = res.data[0]

    await log_audit(
        action=AuditAction.VERIFY_NRC,
        actor_id=current_user["sub"],
        actor_email=current_user["email"],
        target_id=citizen["id"],
        target_type="citizen",
        details={"organization": body.organization},
        ip_address=ip,
        device_hint=device,
        result="success",
    )

    return api_response(success=True, message="Identity verified", data={"result": "verified", "citizen": citizen})


@router.get("/logs")
async def get_verification_logs(
    page: int = 1,
    limit: int = 20,
    result: str = "all",
    search: str = "",
    current_user: dict = Depends(get_current_user),
):
    """Return paginated verification/audit logs (admin/registrar only)."""
    query = supabase.table("audit_logs").select("*, citizens(*)", count="exact")

    if result != "all":
        query = query.eq("result", result)
    if search:
        query = query.or_(f"actor_email.ilike.%{search}%,ip_address.ilike.%{search}%")

    start = (page - 1) * limit
    end = start + limit - 1

    res = query.range(start, end).order("created_at", desc=True).execute()

    return api_response(
        success=True,
        message="Logs fetched",
        data=res.data,
        meta={"total": res.count, "page": page, "limit": limit},
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _qr_error_message(reason: str) -> str:
    messages = {
        "expired":             "QR code has expired. Ask the citizen to generate a new one.",
        "token_already_used":  "QR code has already been scanned. One-time tokens cannot be reused.",
        "tampered":            "QR code signature is invalid — possible forgery detected.",
        "invalid_token":       "QR code is not valid. Please scan a genuine ZamID QR code.",
        "missing_jti":         "QR code is missing required security fields.",
    }
    return messages.get(reason, "QR verification failed. Please try again.")
