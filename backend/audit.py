"""Audit logging helper."""
from datetime import datetime, timezone
from typing import Optional
from database import db
from utils import generate_id


async def log_audit(
    user_id: str,
    user_name: str,
    role: str,
    action: str,
    module: str,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    ip_address: Optional[str] = None,
    operator_id: Optional[str] = None
):
    audit_log = {
        "id": generate_id(),
        "user_id": user_id,
        "user_name": user_name,
        "role": role,
        "action": action,
        "module": module,
        "old_value": old_value,
        "new_value": new_value,
        "ip_address": ip_address,
        "operator_id": operator_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_logs.insert_one(audit_log)
