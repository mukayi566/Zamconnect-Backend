from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, RegisterRequest
from fastapi.responses import JSONResponse
from app.config.supabase import supabase
from app.services.token_service import verify_password, create_access_token, create_refresh_token, decode_token
from app.utils.response import api_response
from app.config.settings import settings
from app.services.audit_service import log_audit
from app.models.enums import AuditAction
from app.services.qr_service import generate_qr_payload
from app.middleware.auth import get_current_user
from app.utils.date import calculate_age
from datetime import datetime, date
from app.schemas.auth import AgeVerificationResponse, DependentCreateRequest



router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
async def login(request: LoginRequest):
    try:
        # 1. Authenticate with Supabase Auth (works for ALL users)
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        user_id = response.user.id

        # 2a. Check citizens table first (mobile app users)
        citizen_res = supabase.table("citizens").select("*").eq("id", user_id).single().execute()
        
        if citizen_res.data:
            citizen = citizen_res.data
            full_name = f"{citizen.get('first_name', '')} {citizen.get('last_name', '')}".strip()
            user_payload = {
                "sub": user_id,
                "email": request.email,
                "role": "citizen",
                "full_name": full_name,
                "type": "citizen",
            }
            access_token = create_access_token(user_payload)
            refresh_token = create_refresh_token(user_payload)

            await log_audit(
                action=AuditAction.LOGIN,
                actor_id=user_id,
                actor_email=request.email,
                target_id=user_id,
                target_type="citizen",
                details={"ip": "0.0.0.0"}
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
                        "role": "citizen",
                        "full_name": full_name,
                    }
                }
            )

        # 2b. Fall back to admin_users table (web admin panel)
        admin_res = supabase.table("admin_users").select("*").eq("id", user_id).single().execute()

        if admin_res.data:
            admin_data = admin_res.data
            user_payload = {
                "sub": user_id,
                "email": request.email,
                "role": admin_data["role"],
                "full_name": admin_data["full_name"],
                "type": "admin",
            }
            access_token = create_access_token(user_payload)
            refresh_token = create_refresh_token(user_payload)

            await log_audit(
                action=AuditAction.LOGIN,
                actor_id=user_id,
                actor_email=request.email,
                target_id=user_id,
                target_type="admin",
                details={"ip": "0.0.0.0"}
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
                        "full_name": admin_data["full_name"],
                    }
                }
            )

        # 3. User authenticated with Supabase but has no profile record
        raise HTTPException(
            status_code=403,
            detail="Account not found. Please complete registration first."
        )

    except HTTPException as he:
        raise he
    except Exception as e:
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
async def register(request: RegisterRequest):
    try:
        # 0. Age Validation
        if request.date_of_birth:
            try:
                dob = datetime.strptime(request.date_of_birth, "%Y-%m-%d").date()
                age = calculate_age(dob)
                if age < 16:
                    return JSONResponse(
                        status_code=400,
                        content=api_response(
                            success=False, 
                            message="Registration failed: Users under the age of 16 are not allowed to register independently. Please complete registration under a parent or guardian account."
                        )
                    )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # 1. Create auth user in Supabase
        auth_res = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_res.user:
            raise HTTPException(status_code=400, detail="Failed to create auth user")
            
        user_id = auth_res.user.id
        full_name = request.full_name or ""
        name_parts = full_name.split(" ")
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # 2. Create citizen record
        citizen_data = {
            "id": user_id,
            "nrc_number": request.nrc or None,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": request.date_of_birth or None,
            "gender": request.gender or "male",
            "phone": request.phone or None,
            "email": request.email,
            "status": "pending",
            "province": request.province or None,
            "district": request.district or None,
            "address": request.address or None,
            "nrc_url": request.nrc_url or None,
            "passport_url": request.passport_url or None,
            "birth_cert_url": request.birth_cert_url or None,
            "selfie_url": request.selfie_url or None,
            "signature_url": request.signature_url or None,
            "signature_url": request.signature_url or None,
            "biometrics_enabled": request.biometrics_enabled or False,
            "guardian_id": request.guardian_id or None,
        }
        
        try:
            qr_payload = generate_qr_payload(citizen_data)
            citizen_data["qr_payload"] = qr_payload
        except Exception:
            citizen_data["qr_payload"] = None
        
        insert_res = supabase.table("citizens").insert(citizen_data).execute()
        
        if not insert_res.data:
            raise HTTPException(status_code=400, detail="Failed to save citizen record")
        
        return JSONResponse(
            status_code=201,
            content=api_response(success=True, message="Registration successful", data={"user_id": user_id})
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content=api_response(success=False, message=str(e))
        )

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return api_response(success=True, message="Profile fetched", data=current_user)

@router.get("/verify-age", response_model=AgeVerificationResponse)
async def verify_age(dob: str):
    try:
        birth_date = datetime.strptime(dob, "%Y-%m-%d").date()
        age = calculate_age(birth_date)
        is_eligible = age >= 16
        return AgeVerificationResponse(
            is_eligible=is_eligible,
            age=age,
            message="Eligible for independent registration" if is_eligible else "Must register under a guardian"
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.post("/dependents")
async def add_dependent(request: DependentCreateRequest, current_user: dict = Depends(get_current_user)):
    try:
        # 1. Calculate age
        dob = datetime.strptime(request.date_of_birth, "%Y-%m-%d").date()
        age = calculate_age(dob)
        
        if age >= 16:
            raise HTTPException(status_code=400, detail="Users 16 and above should register independently.")

        # 2. Prepare citizen data
        # Note: We generate a random ID since dependents don't have a Supabase Auth ID
        import uuid
        dependent_id = str(uuid.uuid4())
        
        name_parts = request.full_name.split(" ")
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Get guardian details from current_user
        guardian_id = current_user["id"]
        guardian_res = supabase.table("citizens").select("*").eq("id", guardian_id).single().execute()
        guardian_data = guardian_res.data
        
        citizen_data = {
            "id": dependent_id,
            "nrc_number": request.nrc or None,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": request.date_of_birth,
            "gender": request.gender,
            "guardian_id": guardian_id,
            "status": "pending",
            # Inherit some location data from guardian
            "province": guardian_data.get("province") if guardian_data else None,
            "district": guardian_data.get("district") if guardian_data else None,
            "address": guardian_data.get("address") if guardian_data else None,
            "birth_cert_url": request.birth_cert_url or None,
        }
        
        qr_payload = generate_qr_payload(citizen_data)
        citizen_data["qr_payload"] = qr_payload
        
        # 3. Insert into database
        insert_res = supabase.table("citizens").insert(citizen_data).execute()
        
        if not insert_res.data:
            raise HTTPException(status_code=400, detail="Failed to save dependent record")
            
        return api_response(
            success=True,
            message="Dependent added successfully",
            data={"dependent_id": dependent_id}
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



