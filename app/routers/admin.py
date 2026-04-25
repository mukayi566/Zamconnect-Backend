from fastapi import APIRouter, Depends
from app.config.supabase import supabase
from app.utils.response import api_response
from app.middleware.auth import role_required
from app.models.enums import UserRole

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(role_required([UserRole.ADMIN]))):
    # Total citizens
    total = supabase.table("citizens").select("*", count="exact").execute()
    
    # Status counts
    active = supabase.table("citizens").select("*", count="exact").eq("status", "active").execute()
    pending = supabase.table("citizens").select("*", count="exact").eq("status", "pending").execute()
    
    # Recent activity (audit logs)
    recent = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(5).execute()
    
    return api_response(
        success=True,
        message="Stats fetched",
        data={
            "total_citizens": total.count,
            "active_count": active.count,
            "pending_count": pending.count,
            "recent_activity": recent.data
        }
    )
