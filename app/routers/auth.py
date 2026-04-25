from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.config.supabase import supabase
from app.services.token_service import verify_password, create_access_token, create_refresh_token, decode_token
from app.utils.response import api_response
from app.config.settings import settings
from app.services.audit_service import log_audit
from app.models.enums import AuditAction
from app.services.qr_service import generate_qr_payload
from app.middleware.auth import get_current_user



router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
async def login(request: LoginRequest):
    try:
        # 1. Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        user_id = response.user.id
        
        # 2. Get admin user details (role, name)
        admin_res = supabase.table("admin_users").select("*").eq("id", user_id).single().execute()
        
        if not admin_res.data:
            raise HTTPException(status_code=403, detail="User not found in admin records")
            
        admin_data = admin_res.data
        
        # 3. Create our own JWTs
        user_payload = {
            "sub": user_id,
            "email": request.email,
            "role": admin_data["role"],
            "full_name": admin_data["full_name"]
        }
        
        access_token = create_access_token(user_payload)
        refresh_token = create_refresh_token(user_payload)
        
        # 4. Audit Log
        await log_audit(
            action=AuditAction.LOGIN,
            actor_id=user_id,
            actor_email=request.email,
            target_id=user_id,
            target_type="admin",
            details={"ip": "0.0.0.0"} # extract from request in production
        )
        
        return api_response(
            success=True,
            message="Login successful",
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user_id,
                    "email": request.email,
                    "role": admin_data["role"],
                    "full_name": admin_data["full_name"]
                }
            }
        )
        
    except Exception as e:
        # Check for specific error codes like account_locked if implemented
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/refresh")
async def refresh(request: RefreshRequest):
    payload = decode_token(request.refresh_token, settings.JWT_REFRESH_SECRET)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    # Re-issue tokens
    user_payload = {
        "sub": payload["sub"],
        "email": payload["email"],
        "role": payload["role"],
        "full_name": payload["full_name"]
    }
    
    access_token = create_access_token(user_payload)
    refresh_token = create_refresh_token(user_payload)
    
    return api_response(
        success=True,
        message="Token refreshed",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    )

@router.post("/register")
async def register(request: Request):
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password required")
            
        # 1. Create auth user in Supabase
        auth_res = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if not auth_res.user:
            raise HTTPException(status_code=400, detail="Failed to create auth user")
            
        user_id = auth_res.user.id
        full_name = body.get("full_name", "")
        name_parts = full_name.split(" ")
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # 2. Create citizen record
        citizen_data = {
            "id": user_id,
            "nrc_number": body.get("nrc") or None,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": body.get("date_of_birth") or None,
            "gender": body.get("gender", "male"),
            "phone": body.get("phone") or None,
            "email": email,
            "status": "pending",
            "province": body.get("province") or None,
            "district": body.get("district") or None,
            "address": body.get("address") or None,
            # Identity document URLs
            "nrc_url": body.get("nrc_url") or None,
            "passport_url": body.get("passport_url") or None,
            "birth_cert_url": body.get("birth_cert_url") or None,
            "selfie_url": body.get("selfie_url") or None,
            "signature_url": body.get("signature_url") or None,
            "biometrics_enabled": body.get("biometrics_enabled", False),
            # Let Supabase handle created_at automatically (do NOT pass "now()" as string)
        }
        
        # Generate QR — safe even if nrc_number is None (basic registration)
        try:
            qr_payload = generate_qr_payload(citizen_data)
            citizen_data["qr_payload"] = qr_payload
        except Exception:
            citizen_data["qr_payload"] = None
        
        insert_res = supabase.table("citizens").insert(citizen_data).execute()
        
        if not insert_res.data:
            raise HTTPException(status_code=400, detail="Failed to save citizen record")
        
        return api_response(success=True, message="Registration successful", data={"user_id": user_id})
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return api_response(success=True, message="Profile fetched", data=current_user)


