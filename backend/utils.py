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
    """Legacy sync fallback — prefer generate_invoice_number_atomic() for concurrency safety."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:18]
    return f"INV-{operator_id[:8].upper()}-{timestamp}"


async def generate_invoice_number_atomic(db_ref) -> str:
    """
    Generate a globally-unique invoice number using an atomic MongoDB counter.
    Format: EBILL-YYYYMM-NNNNNN (zero-padded 6-digit sequence).
    This guarantees no two operators can ever get the same invoice number.
    """
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y%m")  # e.g. "202603"
    result = await db_ref.counters.find_one_and_update(
        {"_id": f"invoice_{month_key}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,  # return the updated document (pymongo 4.x)
    )
    seq = result["seq"]
    return f"EBILL-{month_key}-{seq:06d}"
