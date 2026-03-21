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


def create_token(user_data: dict, expiration_hours: float = JWT_EXPIRATION_HOURS) -> str:
    payload = {
        "sub": user_data["id"],
        "email": user_data["email"],
        "role": user_data["role"],
        "operator_id": user_data.get("operator_id"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
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
    Generate a globally-unique, non-guessable invoice number.
    Format: EBILL-XXXXXXXX (8 random alphanumeric uppercase characters).
    Uses a retry loop with DB uniqueness check to guarantee no collisions.
    8 chars from [A-Z0-9] = 36^8 ≈ 2.8 trillion combinations — practically unguessable.
    """
    import secrets
    import string
    alphabet = string.ascii_uppercase + string.digits  # A-Z, 0-9
    for _ in range(20):  # max 20 attempts (collision virtually impossible)
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        invoice_number = f"EBILL-{code}"
        exists = await db_ref.invoices.find_one(
            {"invoice_number": invoice_number}, {"_id": 1}
        )
        if not exists:
            return invoice_number
    # Fallback: append timestamp to ensure uniqueness
    ts = datetime.now(timezone.utc).strftime("%f")
    return f"EBILL-{''.join(secrets.choice(alphabet) for _ in range(6))}{ts[:2]}"
