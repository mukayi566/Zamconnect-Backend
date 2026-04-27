"""
Audit Service — ZamID Connect

Every verification action generates an immutable forensic log row in `audit_logs`.
Schema written to match government-level auditability requirements:
  - actor (who did the action)
  - target (whose identity was accessed)
  - result (success / fail / tampered / expired / replay)
  - ip_address + device_hint
  - created_at (UTC)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.config.supabase import supabase
from app.models.enums import AuditAction

logger = logging.getLogger("zamid.audit")


async def log_audit(
    action: AuditAction,
    actor_id: str,
    actor_email: str,
    target_id: str,
    target_type: str,
    details: dict,
    ip_address: str = "0.0.0.0",
    device_hint: Optional[str] = None,
    result: str = "success",
) -> None:
    """
    Write a structured audit record.

    Args:
        action       — AuditAction enum value
        actor_id     — UUID of the user/officer performing the action
        actor_email  — email for quick lookup
        target_id    — UUID of the citizen being accessed
        target_type  — "citizen" | "admin" | "system"
        details      — arbitrary JSON context (organisation, scan method, etc.)
        ip_address   — caller's IP (extracted by router from Request object)
        device_hint  — User-Agent snippet for device fingerprinting
        result       — "success" | "fail" | "tampered" | "expired" | "replay"
    """
    record = {
        "action":      action.value if hasattr(action, "value") else action,
        "actor_id":    actor_id,
        "actor_email": actor_email,
        "target_id":   target_id,
        "target_type": target_type,
        "details":     details,
        "ip_address":  ip_address,
        "device_hint": device_hint,
        "result":      result,
        "created_at":  datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase.table("audit_logs").insert(record).execute()
    except Exception as exc:
        # Audit failure must NEVER crash the main request — log and continue
        logger.error("Failed to write audit log: %s | record=%s", exc, record)
