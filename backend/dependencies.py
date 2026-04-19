"""FastAPI dependency functions for authentication and authorization."""
from fastapi import Depends, HTTPException, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from database import db
from utils import decode_token

security = HTTPBearer(auto_error=False)  # Make it optional to support cookies

DEFAULT_MAINTENANCE_MESSAGE = "The app is under maintenance. Updates and automation are temporarily paused."


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(default=None)
) -> dict:
    # Try to get token from cookie first, then fallback to Authorization header
    token = None
    if access_token:
        token = access_token
    elif credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(token)
    user = await db.users.find_one({"id": payload["sub"], "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_session_id = payload.get("sid")
    active_session_id = user.get("active_session_id")
    if not payload.get("impersonated_by") and active_session_id and token_session_id != active_session_id:
        raise HTTPException(
            status_code=401,
            detail="Session expired. You have been logged out because your account was used on another device.",
        )
    
    # Carry impersonated_by from JWT payload if present
    if payload.get("impersonated_by"):
        user["impersonated_by"] = payload["impersonated_by"]
    # Extract client IP address for audit logging
    forwarded_for = request.headers.get("X-Forwarded-For")
    user["_ip_address"] = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else None)
    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_operator(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] not in ["operator", "admin", "staff"]:
        raise HTTPException(status_code=403, detail="Operator access required")
    return current_user


async def require_operator_no_staff(current_user: dict = Depends(get_current_user)) -> dict:
    """Only operators (not staff) can perform this action."""
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff users cannot perform delete operations")
    if current_user["role"] not in ["operator", "admin"]:
        raise HTTPException(status_code=403, detail="Operator access required")
    return current_user


async def get_platform_settings() -> dict:
    return await db.global_settings.find_one({"type": "platform"}, {"_id": 0}) or {}


async def get_platform_maintenance_state() -> dict:
    settings = await get_platform_settings()
    return {
        "maintenance_mode": bool(settings.get("maintenance_mode", False)),
        "maintenance_message": settings.get("maintenance_message") or DEFAULT_MAINTENANCE_MESSAGE,
    }


async def get_operator_access_state(operator_id: str) -> dict:
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    maintenance = await get_platform_maintenance_state()
    operator_read_only = bool(operator.get("is_read_only")) if operator else False
    return {
        "operator": operator,
        "maintenance_mode": maintenance["maintenance_mode"],
        "maintenance_message": maintenance["maintenance_message"],
        "is_read_only": operator_read_only or maintenance["maintenance_mode"],
    }


async def check_operator_read_only(operator_id: str) -> bool:
    state = await get_operator_access_state(operator_id)
    return state["is_read_only"]
