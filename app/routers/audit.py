from fastapi import APIRouter, HTTPException, Depends, Query
from app.config.supabase import supabase
from app.utils.response import api_response
from app.middleware.auth import role_required
from app.models.enums import UserRole

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("/logs")
async def get_audit_logs(
    page: int = 1,
    limit: int = 30,
    action: str = "all",
    search: str = "",
    current_user: dict = Depends(role_required([UserRole.ADMIN]))
):
    query = supabase.table("audit_logs").select("*", count="exact")
    
    if action != "all":
        query = query.eq("action", action)
    if search:
        query = query.ilike("actor_email", f"%{search}%")
        
    start = (page - 1) * limit
    end = start + limit - 1
    
    res = query.range(start, end).order("created_at", desc=True).execute()
    
    return api_response(
        success=True,
        message="Audit logs fetched",
        data=res.data,
        meta={"total": res.count, "page": page, "limit": limit}
    )
