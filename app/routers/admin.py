from fastapi import APIRouter, Depends
from app.config.supabase import supabase
from app.utils.response import api_response
from app.middleware.auth import role_required
from app.models.enums import UserRole, AuditAction
from datetime import datetime, date

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(role_required([UserRole.ADMIN]))):
    # Total citizens
    total = supabase.table("citizens").select("*", count="exact").execute()
    
    # Status counts
    active = supabase.table("citizens").select("*", count="exact").eq("status", "active").execute()
    pending = supabase.table("citizens").select("*", count="exact").eq("status", "pending").execute()
    suspended = supabase.table("citizens").select("*", count="exact").eq("status", "suspended").execute()
    rejected = supabase.table("citizens").select("*", count="exact").eq("status", "rejected").execute()
    
    
    # Verifications Today
    today = date.today().isoformat()
    verifications = supabase.table("audit_logs").select("*", count="exact")\
        .in_("action", [AuditAction.VERIFY_QR, AuditAction.VERIFY_NRC])\
        .gte("created_at", today)\
        .execute()
    
    # Recent activity (audit logs)
    recent = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(5).execute()
    
    return api_response(
        success=True,
        message="Stats fetched",
        data={
            "total_citizens": total.count,
            "active_count": active.count,
            "pending_count": pending.count,
            "suspended_count": suspended.count,
            "rejected_count": rejected.count,
            "verifications_today": verifications.count,
            "recent_activity": recent.data
        }
    )
