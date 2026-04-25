from app.config.supabase import supabase
from app.models.enums import AuditAction
from datetime import datetime

async def log_audit(
    action: AuditAction,
    actor_id: str,
    actor_email: str,
    target_id: str,
    target_type: str,
    details: dict,
    ip_address: str = "0.0.0.0"
):
    try:
        supabase.table("audit_logs").insert({
            "action": action,
            "actor_id": actor_id,
            "actor_email": actor_email,
            "target_id": target_id,
            "target_type": target_type,
            "details": details,
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        # In production, use structured logging
        print(f"Failed to write audit log: {e}")
