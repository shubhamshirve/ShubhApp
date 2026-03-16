"""Utility functions: ID generation, password hashing, JWT, invoice number."""
import uuid
import bcrypt
import jwt
import logging
from datetime import datetime, timezone, timedelta
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def generate_id() -> str:
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_token(user_data: dict) -> str:
    payload = {
        "sub": user_data["id"],
        "email": user_data["email"],
        "role": user_data["role"],
        "operator_id": user_data.get("operator_id"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    if user_data.get("impersonated_by"):
        payload["impersonated_by"] = user_data["impersonated_by"]
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_invoice_number(operator_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"INV-{operator_id[:8].upper()}-{timestamp}"
