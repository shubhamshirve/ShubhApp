"""Error logging utility for storing application errors in MongoDB."""
import logging
from datetime import datetime, timezone
from database import db
from utils import generate_id

logger = logging.getLogger(__name__)


async def log_error(
    error_type: str,
    message: str,
    module: str = "",
    endpoint: str = "",
    user_id: str = None,
    user_name: str = None,
    user_role: str = None,
    operator_id: str = None,
    request_method: str = "",
    request_path: str = "",
    status_code: int = 500,
    stack_trace: str = "",
    extra_data: dict = None,
    ip_address: str = "",
):
    """Log an error to the error_logs collection."""
    try:
        now = datetime.now(timezone.utc)
        error_log = {
            "id": generate_id(),
            "error_type": error_type,
            "message": message,
            "module": module,
            "endpoint": endpoint,
            "user_id": user_id,
            "user_name": user_name or "System",
            "user_role": user_role or "system",
            "operator_id": operator_id,
            "request_method": request_method,
            "request_path": request_path,
            "status_code": status_code,
            "stack_trace": stack_trace,
            "extra_data": extra_data or {},
            "ip_address": ip_address,
            "created_at": now.isoformat(),
        }
        await db.error_logs.insert_one(error_log)
    except Exception as e:
        logger.error(f"Failed to log error: {e}")
