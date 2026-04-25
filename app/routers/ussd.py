from fastapi import APIRouter, Request, Response
from app.config.supabase import supabase
from app.models.enums import CitizenStatus

router = APIRouter(prefix="/ussd", tags=["USSD"])

@router.post("")
async def ussd_handler(request: Request):
    # AT sends data in application/x-www-form-urlencoded
    form_data = await request.form()
    
    session_id = form_data.get("sessionId")
    service_code = form_data.get("serviceCode")
    phone_number = form_data.get("phoneNumber")
    text = form_data.get("text", "")
    
    parts = text.split("*") if text else []
    level = len(parts)
    
    response_text = ""
    
    if text == "":
        # Main Menu
        response_text = "CON Welcome to ZamID Connect - *222#\n"
        response_text += "1. Check ID Status\n"
        response_text += "2. Verify NRC Number\n"
        response_text += "3. Report Lost NRC\n"
        response_text += "4. My Wallet/Services\n"
        response_text += "0. Exit"
    
    elif parts[0] == "1":
        # Check ID Status
        if level == 1:
            response_text = "CON Enter your NRC Number (000000/00/0):"
        else:
            nrc = parts[1]
            res = supabase.table("citizens").select("first_name,last_name,status").eq("nrc_number", nrc).execute()
            if res.data:
                c = res.data[0]
                response_text = f"END Name: {c['first_name']} {c['last_name']}\nStatus: {c['status'].upper()}"
            else:
                response_text = "END NRC not found in our records."
                
    elif parts[0] == "2":
        # Verify NRC
        if level == 1:
            response_text = "CON Enter NRC to verify:"
        else:
            nrc = parts[1]
            res = supabase.table("citizens").select("id").eq("nrc_number", nrc).eq("status", "active").execute()
            if res.data:
                response_text = f"END Identity VERIFIED for NRC {nrc}."
            else:
                response_text = f"END Identity NOT FOUND or INACTIVE for NRC {nrc}."
                
    elif parts[0] == "3":
        response_text = "END Service unavailable. Please visit the nearest registrar office."
        
    elif parts[0] == "0":
        response_text = "END Thank you for using ZamID Connect."
    
    else:
        response_text = "END Invalid option."

    return Response(content=response_text, media_type="text/plain")
