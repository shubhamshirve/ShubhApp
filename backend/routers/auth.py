"""Auth router: register, login, me."""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta

from database import db
from models import OperatorCreate, UserLogin, UserResponse, TokenResponse
from utils import generate_id, hash_password, verify_password, create_token
from dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register_operator(data: OperatorCreate):
    """Register a new operator with trial period."""
    existing = await db.users.find_one({"email": data.email, "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    trial_plan = await db.saas_plans.find_one({"trial_enabled": True, "deleted_at": None}, {"_id": 0})

    now = datetime.now(timezone.utc)
    operator_id = generate_id()
    user_id = generate_id()

    operator = {
        "id": operator_id,
        "company_name": data.company_name,
        "owner_name": data.owner_name,
        "email": data.email,
        "phone": data.phone,
        "gst_number": data.gst_number,
        "charge_gst": data.charge_gst,
        "bank_account_name": data.bank_account_name,
        "bank_account_number": data.bank_account_number,
        "bank_ifsc": data.bank_ifsc,
        "bank_name": data.bank_name,
        "status": "trial",
        "saas_plan_id": trial_plan["id"] if trial_plan else None,
        "saas_plan_name": trial_plan["name"] if trial_plan else None,
        "trial_ends_at": (now + timedelta(days=trial_plan["trial_days"] if trial_plan else 3)).isoformat(),
        "subscription_ends_at": None,
        "is_read_only": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.operators.insert_one(operator)

    user = {
        "id": user_id,
        "email": data.email,
        "name": data.owner_name,
        "phone": data.phone,
        "password": hash_password(data.password),
        "role": "operator",
        "operator_id": operator_id,
        "status": "active",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.users.insert_one(user)

    token = create_token({"id": user_id, "email": data.email, "role": "operator", "operator_id": operator_id})

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id, email=data.email, name=data.owner_name,
            phone=data.phone, role="operator", operator_id=operator_id,
            status="active", created_at=now
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    """Login for all users."""
    user = await db.users.find_one({"email": data.email, "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user["status"] != "active":
        raise HTTPException(status_code=401, detail="Account is not active")

    token = create_token({
        "id": user["id"], "email": user["email"],
        "role": user["role"], "operator_id": user.get("operator_id")
    })

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"], email=user["email"], name=user["name"],
            phone=user.get("phone"), role=user["role"],
            operator_id=user.get("operator_id"), status=user["status"],
            created_at=datetime.fromisoformat(user["created_at"])
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=current_user["id"], email=current_user["email"],
        name=current_user["name"], phone=current_user.get("phone"),
        role=current_user["role"], operator_id=current_user.get("operator_id"),
        status=current_user["status"],
        impersonated_by=current_user.get("impersonated_by"),
        created_at=datetime.fromisoformat(current_user["created_at"])
    )
