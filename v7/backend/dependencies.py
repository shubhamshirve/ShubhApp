"""FastAPI dependency functions for authentication and authorization."""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import db
from utils import decode_token

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    user = await db.users.find_one({"id": payload["sub"], "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
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


async def check_operator_read_only(operator_id: str) -> bool:
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if operator and operator.get("is_read_only"):
        return True
    return False
