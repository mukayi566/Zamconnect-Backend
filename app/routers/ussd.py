from fastapi import APIRouter, Request, Response
from app.config.supabase import supabase
from app.models.enums import CitizenStatus, AuditAction
from datetime import datetime, timezone
from app.utils.ssn import generate_ssn
import uuid
from app.services.qr_service import generate_qr_payload

router = APIRouter(prefix="/ussd", tags=["USSD"])


def log_ussd_session(session_id: str, phone_number: str, action: str, details: str = ""):
    """Log USSD interactions to Supabase audit table."""
    try:
        supabase.table("audit_logs").insert({
            "action": AuditAction.USSD_ACCESS.value,
            "details": f"[{action}] Phone: {phone_number} | {details}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass  # Never let audit logging break the USSD flow


@router.post("")
async def ussd_handler(request: Request):
    """
    Africa's Talking USSD callback endpoint.
    Expects application/x-www-form-urlencoded with fields:
      sessionId, serviceCode, phoneNumber, text
    """
    # AT sends data in application/x-www-form-urlencoded
    form_data = await request.form()

    session_id   = form_data.get("sessionId", "")
    service_code = form_data.get("serviceCode", "")
    phone_number = form_data.get("phoneNumber", "")
    text         = form_data.get("text", "")

    parts = text.split("*") if text else []
    level = len(parts)

    response_text = ""

    # ── Main Menu ───────────────────────────────────────────────
    if text == "":
        log_ussd_session(session_id, phone_number, "MENU_OPEN")
        response_text = (
            "CON Welcome to ZamID Connect\n"
            "1. Check ID Status\n"
            "2. Verify NRC Number\n"
            "3. Create Account\n"
            "4. Report Lost NRC\n"
            "5. Help & Info\n"
            "0. Exit"
        )

    # ── Option 1: Check ID Status ────────────────────────────────
    elif parts[0] == "1":
        if level == 1:
            response_text = "CON Enter your NRC Number (e.g. 123456/78/9):"
        else:
            nrc = parts[1].strip()
            try:
                res = supabase.table("citizens") \
                    .select("first_name,last_name,status") \
                    .eq("nrc_number", nrc) \
                    .execute()

                if res.data:
                    c = res.data[0]
                    status_label = c["status"].upper()
                    log_ussd_session(session_id, phone_number, "ID_STATUS_CHECK",
                                     f"NRC={nrc} Status={status_label}")
                    response_text = (
                        f"END Name: {c['first_name']} {c['last_name']}\n"
                        f"NRC: {nrc}\n"
                        f"Status: {status_label}"
                    )
                else:
                    log_ussd_session(session_id, phone_number, "ID_STATUS_NOT_FOUND", f"NRC={nrc}")
                    response_text = f"END No record found for NRC {nrc}.\nVisit your nearest registrar."
            except Exception as e:
                response_text = "END Service temporarily unavailable. Please try again later."

    # ── Option 2: Verify NRC ─────────────────────────────────────
    elif parts[0] == "2":
        if level == 1:
            response_text = "CON Enter NRC Number to verify:"
        else:
            nrc = parts[1].strip()
            try:
                res = supabase.table("citizens") \
                    .select("id,first_name,last_name") \
                    .eq("nrc_number", nrc) \
                    .eq("status", CitizenStatus.ACTIVE.value) \
                    .execute()

                if res.data:
                    c = res.data[0]
                    log_ussd_session(session_id, phone_number, "NRC_VERIFIED", f"NRC={nrc}")
                    response_text = (
                        f"END ✔ VERIFIED\n"
                        f"NRC {nrc} is valid.\n"
                        f"Holder: {c['first_name']} {c['last_name']}"
                    )
                else:
                    log_ussd_session(session_id, phone_number, "NRC_NOT_VERIFIED", f"NRC={nrc}")
                    response_text = (
                        f"END ✘ NOT VERIFIED\n"
                        f"NRC {nrc} is not active or not found."
                    )
            except Exception:
                response_text = "END Service temporarily unavailable. Please try again later."

    # ── Option 3: Create Account ────────────────────────────────
    elif parts[0] == "3":
        if level == 1:
            response_text = "CON Create ZamID Account\nEnter NRC Number (e.g. 123456/78/9):"
        elif level == 2:
            response_text = "CON Enter First Name:"
        elif level == 3:
            response_text = "CON Enter Last Name:"
        elif level == 4:
            response_text = "CON Select Gender:\n1. Male\n2. Female"
        elif level == 5:
            response_text = "CON Enter Place of Birth (Province):"
        elif level == 6:
            nrc = parts[1].strip()
            fname = parts[2].strip()
            lname = parts[3].strip()
            gender_code = parts[4].strip()
            place = parts[5].strip()
            
            gender = "Male" if gender_code == "1" else "Female"
            ssn = generate_ssn()
            citizen_id = str(uuid.uuid4())
            
            try:
                # Check if NRC already exists
                existing = supabase.table("citizens").select("id").eq("nrc_number", nrc).execute()
                if existing.data:
                    response_text = f"END Error: NRC {nrc} is already registered."
                else:
                    # Insert new citizen
                    citizen_data = {
                        "id": citizen_id,
                        "nrc_number": nrc,
                        "first_name": fname,
                        "last_name": lname,
                        "gender": gender,
                        "province": place,
                        "status": CitizenStatus.PENDING.value,
                        "registration_type": "ussd",
                        "date_of_birth": "2000-01-01", # Default for USSD
                        "phone": phone_number,
                        "ssn": ssn
                    }
                    
                    # Generate QR Payload
                    try:
                        citizen_data["qr_payload"] = generate_qr_payload(citizen_data)
                    except Exception as qr_err:
                        print(f"USSD QR Generation Error: {qr_err}")
                        citizen_data["qr_payload"] = None

                    try:
                        supabase.table("citizens").insert(citizen_data).execute()
                        log_ussd_session(session_id, phone_number, "ACCOUNT_CREATED", f"NRC={nrc} SSN={ssn}")
                        response_text = (
                            f"END Success! Account created for {fname} {lname}.\n"
                            f"Your NRC: {nrc}\n"
                            f"Generated SSN: {ssn}\n"
                            f"Visit a registrar to activate."
                        )
                    except Exception as e:
                        # Fallback if ssn column is missing
                        if "column \"ssn\"" in str(e):
                            del citizen_data["ssn"]
                            supabase.table("citizens").insert(citizen_data).execute()
                            log_ussd_session(session_id, phone_number, "ACCOUNT_CREATED", f"NRC={nrc}")
                            response_text = (
                                f"END Account created for {fname} {lname}.\n"
                                f"NRC: {nrc}\n"
                                f"Generated SSN: {ssn}\n"
                                f"Note: SSN generated but not saved to DB."
                            )
                        else:
                            raise e
            except Exception as e:
                print(f"USSD Registration Error: {str(e)}")
                response_text = "END Service temporarily unavailable. Please try again later."

    # ── Option 4: Report Lost NRC ────────────────────────────────
    elif parts[0] == "4":
        if level == 1:
            response_text = (
                "CON Report Lost NRC:\n"
                "1. Get Reporting Steps\n"
                "0. Back"
            )
        elif parts[1] == "1":
            log_ussd_session(session_id, phone_number, "LOST_NRC_INFO")
            response_text = (
                "END Lost NRC Steps:\n"
                "1. Visit nearest police station\n"
                "2. Obtain police report\n"
                "3. Go to immigration office\n"
                "4. Pay replacement fee\n"
                "Hotline: 0800-ZAMID-1"
            )
        else:
            response_text = "END Invalid option."

    # ── Option 5: Help & Info ─────────────────────────────────────
    elif parts[0] == "5":
        log_ussd_session(session_id, phone_number, "HELP_INFO")
        response_text = (
            "END ZamID Connect Help:\n"
            "Website: zamid.gov.zm\n"
            "Email: support@zamid.gov.zm\n"
            "Hotline: 0800-ZAMID-1\n"
            "Hours: Mon-Fri 08:00-17:00"
        )

    # ── Option 0: Exit ────────────────────────────────────────────
    elif parts[0] == "0":
        log_ussd_session(session_id, phone_number, "SESSION_EXIT")
        response_text = "END Thank you for using ZamID Connect.\nDial *384*98008# anytime."

    # ── Unknown ───────────────────────────────────────────────────
    else:
        response_text = "END Invalid option. Please dial *384*98008# again."

    return Response(content=response_text, media_type="text/plain")
