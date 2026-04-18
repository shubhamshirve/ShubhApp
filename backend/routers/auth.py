"""Auth router: register (with OTP), login, me."""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone, timedelta
import random
import logging

from database import db
from models import OperatorCreate, UserLogin, UserResponse, TokenResponse
from utils import generate_id, hash_password, verify_password, create_token, generate_unique_referral_code
from dependencies import get_current_user, get_platform_maintenance_state, get_operator_access_state
from audit import log_audit
from sanitization import SanitizedModel, sanitize_text
from services.email_service import get_email_service_async, EmailServiceError

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 30
OTP_MAX_RESENDS = 5
OTP_EXPIRY_MINUTES = 10
RECOVERY_OTP_EXPIRY_MINUTES = 15


class OTPVerifyRequest(SanitizedModel):
    registration_id: str
    otp: str


def _generate_otp() -> str:
    return str(random.randint(10 ** (OTP_LENGTH - 1), (10 ** OTP_LENGTH) - 1))


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*" * max(0, len(local) - 1)
    else:
        masked_local = local[:2] + "*" * (len(local) - 2)
    return f"{masked_local}@{domain}"


async def _send_registration_otp_email(email: str, otp: str):
    service = await get_email_service_async()
    await service.send_email(
        to_email=email,
        subject="Your E-Bill registration OTP",
        text=f"Your E-Bill registration OTP is {otp}. It is valid for {OTP_EXPIRY_MINUTES} minutes.",
        html=(
            "<p>Your E-Bill registration OTP is "
            f"<strong>{otp}</strong>.</p>"
            f"<p>This code is valid for {OTP_EXPIRY_MINUTES} minutes.</p>"
            "<p>If you did not request this, you can ignore this email.</p>"
        ),
    )


async def _send_recovery_otp_email(email: str, otp: str):
    service = await get_email_service_async()
    await service.send_email(
        to_email=email,
        subject="Your E-Bill password recovery OTP",
        text=f"Your E-Bill password recovery OTP is {otp}. It is valid for {RECOVERY_OTP_EXPIRY_MINUTES} minutes.",
        html=(
            "<p>Your E-Bill password recovery OTP is "
            f"<strong>{otp}</strong>.</p>"
            f"<p>This code is valid for {RECOVERY_OTP_EXPIRY_MINUTES} minutes.</p>"
            "<p>If you did not request a password reset, please ignore this email.</p>"
        ),
    )


async def _issue_user_session(user: dict, *, update_fields=None) -> str:
    settings = await db.global_settings.find_one({"type": "platform"}) or {}
    timeout = float(settings.get("session_timeout_hours", 24.0))
    session_id = generate_id()
    fields = {
        "active_session_id": session_id,
        "last_login_at": datetime.now(timezone.utc).isoformat(),
    }
    if update_fields:
        fields.update(update_fields)
    await db.users.update_one({"id": user["id"]}, {"$set": fields})
    return create_token(
        {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "operator_id": user.get("operator_id"),
            "session_id": session_id,
        },
        expiration_hours=timeout,
    )


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _enforce_resend_limits(record: dict, now: datetime):
    resend_count = record.get("resend_count", 0)
    if resend_count >= OTP_MAX_RESENDS:
        raise HTTPException(status_code=429, detail="Maximum OTP resend limit reached. Please start again.")

    last_sent_at = record.get("last_sent_at")
    if last_sent_at:
        seconds_since_last_send = (now - _parse_dt(last_sent_at)).total_seconds()
        if seconds_since_last_send < OTP_RESEND_COOLDOWN_SECONDS:
            wait_seconds = int(OTP_RESEND_COOLDOWN_SECONDS - seconds_since_last_send)
            raise HTTPException(status_code=429, detail=f"Please wait {wait_seconds}s before requesting a new OTP.")


@router.post("/register-init")
async def register_init(data: OperatorCreate):
    """Step 1: Validate registration data, check uniqueness, send OTP via email."""
    # Validate email uniqueness
    existing_email = await db.users.find_one({"email": data.email, "deleted_at": None})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate phone uniqueness
    phone_digits = ''.join(c for c in data.phone if c.isdigit())
    if len(phone_digits) == 10:
        phone_digits = "91" + phone_digits
    # Check in operators collection
    existing_phone = await db.operators.find_one({
        "phone": {"$in": [data.phone, phone_digits, phone_digits[-10:]]},
        "deleted_at": None
    })
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    # Also check in users collection
    existing_user_phone = await db.users.find_one({
        "phone": {"$in": [data.phone, phone_digits, phone_digits[-10:]]},
        "deleted_at": None
    })
    if existing_user_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Generate 6-digit OTP
    otp = _generate_otp()
    now = datetime.now(timezone.utc)
    registration_id = generate_id()

    # Store pending registration
    pending = {
        "id": registration_id,
        "company_name": data.company_name,
        "owner_name": data.owner_name,
        "email": data.email,
        "phone": data.phone,
        "password": data.password,  # Will be hashed on completion
        "business_type": data.business_type,
        "gst_number": data.gst_number,
        "pan_number": data.pan_number,
        "address": data.address,
        "charge_gst": data.charge_gst,
        "bank_account_name": data.bank_account_name,
        "bank_account_number": data.bank_account_number,
        "bank_ifsc": data.bank_ifsc,
        "bank_name": data.bank_name,
        "referred_by_code": data.referral_code.upper().strip() if data.referral_code else None,
        "otp": otp,
        "otp_attempts": 0,
        "resend_count": 0,
        "created_at": now.isoformat(),
        "last_sent_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat(),
    }
    # Remove any existing pending registration for this email/phone
    await db.pending_registrations.delete_many({"$or": [{"email": data.email}, {"phone": data.phone}]})
    await db.pending_registrations.insert_one(pending)

    try:
        await _send_registration_otp_email(data.email, otp)
        logger.info("Registration OTP sent via email to %s", _mask_email(data.email))
    except EmailServiceError as exc:
        await db.pending_registrations.delete_one({"id": registration_id})
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "registration_id": registration_id,
        "message": "OTP sent to your email address.",
        "otp_sent": True,
        "email_masked": _mask_email(data.email),
    }


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_and_register(data: OTPVerifyRequest):
    """Step 2: Verify OTP and complete registration."""
    pending = await db.pending_registrations.find_one({"id": data.registration_id}, {"_id": 0})
    if not pending:
        raise HTTPException(status_code=400, detail="Registration session not found or expired. Please start again.")

    # Check expiry
    expires_at = _parse_dt(pending["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.pending_registrations.delete_one({"id": data.registration_id})
        raise HTTPException(status_code=400, detail="OTP has expired. Please register again.")

    # Check attempts
    if pending.get("otp_attempts", 0) >= OTP_MAX_ATTEMPTS:
        await db.pending_registrations.delete_one({"id": data.registration_id})
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please register again.")

    if data.otp != pending["otp"]:
        await db.pending_registrations.update_one(
            {"id": data.registration_id},
            {"$inc": {"otp_attempts": 1}}
        )
        remaining = OTP_MAX_ATTEMPTS - pending.get("otp_attempts", 0) - 1
        raise HTTPException(status_code=400, detail=f"Invalid OTP. {remaining} attempts remaining.")

    # OTP verified - complete registration
    # Re-check uniqueness (in case someone registered between init and verify)
    existing_email = await db.users.find_one({"email": pending["email"], "deleted_at": None})
    if existing_email:
        await db.pending_registrations.delete_one({"id": data.registration_id})
        raise HTTPException(status_code=400, detail="Email already registered")

    # Find the Pro plan for trial (fallback to any plan if Pro not found)
    pro_plan = await db.saas_plans.find_one(
        {"name": {"$regex": "^Pro", "$options": "i"}, "deleted_at": None},
        {"_id": 0}
    )
    if not pro_plan:
        # Fallback to any active plan if Pro plan doesn't exist
        pro_plan = await db.saas_plans.find_one(
            {"deleted_at": None},
            {"_id": 0},
            sort=[("monthly_price", 1)]
        )

    now = datetime.now(timezone.utc)
    operator_id = generate_id()
    user_id = generate_id()
    session_id = generate_id()
    trial_end = (now + timedelta(days=3)).isoformat()

    # Validate referral code if provided
    referred_by_code = pending.get("referred_by_code")
    referral_discount_eligible = False
    if referred_by_code:
        referrer = await db.operators.find_one({"referral_code": referred_by_code, "deleted_at": None})
        if referrer:
            referral_discount_eligible = True
        else:
            referred_by_code = None  # Invalid code, ignore

    # Generate unique referral code for the new operator
    new_referral_code = await generate_unique_referral_code(db)

    operator = {
        "id": operator_id,
        "company_name": pending["company_name"],
        "owner_name": pending["owner_name"],
        "email": pending["email"],
        "phone": pending["phone"],
        "business_type": pending.get("business_type"),
        "gst_number": pending.get("gst_number"),
        "pan_number": pending.get("pan_number"),
        "address": pending.get("address"),
        "charge_gst": pending.get("charge_gst", False),
        "bank_account_name": pending.get("bank_account_name"),
        "bank_account_number": pending.get("bank_account_number"),
        "bank_ifsc": pending.get("bank_ifsc"),
        "bank_name": pending.get("bank_name"),
        "status": "trial",
        "saas_plan_id": pro_plan["id"] if pro_plan else None,
        "saas_plan_name": pro_plan["name"] if pro_plan else None,
        "trial_ends_at": trial_end,
        "subscription_ends_at": trial_end,
        "is_read_only": False,
        "referral_code": new_referral_code,
        "referred_by_code": referred_by_code,
        "referral_discount_eligible": referral_discount_eligible,
        "referral_discount_used": False,
        "wallet_suspended": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.operators.insert_one(operator)

    user = {
        "id": user_id,
        "email": pending["email"],
        "name": pending["owner_name"],
        "phone": pending["phone"],
        "password": hash_password(pending["password"]),
        "role": "operator",
        "operator_id": operator_id,
        "status": "active",
        "active_session_id": session_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.users.insert_one(user)

    # Create wallet and credit Rs. 100 trial bonus
    from routers.wallet import credit_wallet
    await credit_wallet(
        operator_id=operator_id,
        amount=100.0,
        description="Trial bonus - Welcome credit",
        reference_id=None,
        tx_type="trial_bonus"
    )

    # Clean up pending registration
    await db.pending_registrations.delete_one({"id": data.registration_id})

    settings = await db.global_settings.find_one({"type": "platform"}) or {}
    timeout = float(settings.get("session_timeout_hours", 24.0))
    token = create_token(
        {
            "id": user_id,
            "email": pending["email"],
            "role": "operator",
            "operator_id": operator_id,
            "session_id": session_id,
        },
        expiration_hours=timeout,
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id, email=pending["email"], name=pending["owner_name"],
            phone=pending["phone"], role="operator", operator_id=operator_id,
            status="active", created_at=now
        )
    )


@router.post("/resend-otp")
async def resend_otp(registration_id: str = ""):
    """Resend OTP for a pending registration."""
    registration_id = sanitize_text(registration_id)
    if not registration_id:
        raise HTTPException(status_code=400, detail="Registration ID is required")
    pending = await db.pending_registrations.find_one({"id": registration_id}, {"_id": 0})
    if not pending:
        raise HTTPException(status_code=400, detail="Registration session not found or expired.")

    expires_at = _parse_dt(pending["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.pending_registrations.delete_one({"id": registration_id})
        raise HTTPException(status_code=400, detail="Session expired. Please register again.")

    now = datetime.now(timezone.utc)
    _enforce_resend_limits(pending, now)
    new_otp = _generate_otp()
    await db.pending_registrations.update_one(
        {"id": registration_id},
        {"$set": {
            "otp": new_otp,
            "otp_attempts": 0,
            "last_sent_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat(),
        }, "$inc": {"resend_count": 1}}
    )

    try:
        await _send_registration_otp_email(pending["email"], new_otp)
        logger.info("Registration OTP resent via email to %s", _mask_email(pending["email"]))
    except EmailServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "message": "OTP resent to your email.",
        "otp_sent": True,
        "email_masked": _mask_email(pending["email"]),
    }


# Keep old register endpoint for backward compatibility (deprecated)
@router.post("/register", response_model=TokenResponse)
async def register_operator(data: OperatorCreate):
    """Register a new operator with 3-day trial on the lowest available plan."""
    existing = await db.users.find_one({"email": data.email, "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check phone uniqueness
    phone_digits = ''.join(c for c in data.phone if c.isdigit())
    existing_phone = await db.operators.find_one({
        "phone": {"$in": [data.phone, phone_digits, phone_digits[-10:] if len(phone_digits) >= 10 else phone_digits]},
        "deleted_at": None
    })
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Find the lowest-priced plan (not deleted) for the trial
    lowest_plan = await db.saas_plans.find_one(
        {"deleted_at": None},
        {"_id": 0},
        sort=[("monthly_price", 1)]
    )

    now = datetime.now(timezone.utc)
    operator_id = generate_id()
    user_id = generate_id()
    session_id = generate_id()

    # Set subscription to expire in 3 days
    trial_end = (now + timedelta(days=3)).isoformat()

    # Validate referral code
    referred_by_code = data.referral_code.upper().strip() if data.referral_code else None
    referral_discount_eligible = False
    if referred_by_code:
        referrer = await db.operators.find_one({"referral_code": referred_by_code, "deleted_at": None})
        if referrer:
            referral_discount_eligible = True
        else:
            referred_by_code = None

    new_referral_code = await generate_unique_referral_code(db)

    operator = {
        "id": operator_id,
        "company_name": data.company_name,
        "owner_name": data.owner_name,
        "email": data.email,
        "phone": data.phone,
        "business_type": data.business_type,
        "gst_number": data.gst_number,
        "pan_number": data.pan_number,
        "address": data.address,
        "charge_gst": data.charge_gst,
        "bank_account_name": data.bank_account_name,
        "bank_account_number": data.bank_account_number,
        "bank_ifsc": data.bank_ifsc,
        "bank_name": data.bank_name,
        "status": "trial",
        "saas_plan_id": lowest_plan["id"] if lowest_plan else None,
        "saas_plan_name": lowest_plan["name"] if lowest_plan else None,
        "trial_ends_at": trial_end,
        "subscription_ends_at": trial_end,
        "is_read_only": False,
        "referral_code": new_referral_code,
        "referred_by_code": referred_by_code,
        "referral_discount_eligible": referral_discount_eligible,
        "referral_discount_used": False,
        "wallet_suspended": False,
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
        "active_session_id": session_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.users.insert_one(user)

    settings = await db.global_settings.find_one({"type": "platform"}) or {}
    timeout = float(settings.get("session_timeout_hours", 24.0))
    token = create_token(
        {
            "id": user_id,
            "email": data.email,
            "role": "operator",
            "operator_id": operator_id,
            "session_id": session_id,
        },
        expiration_hours=timeout,
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id, email=data.email, name=data.owner_name,
            phone=data.phone, role="operator", operator_id=operator_id,
            status="active", created_at=now
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request):
    """Login for all users."""
    ip_address = request.headers.get("X-Forwarded-For", request.client.host if request.client else None)

    user = await db.users.find_one({"email": data.email, "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user["status"] != "active":
        raise HTTPException(status_code=401, detail="Account is not active")

    token = await _issue_user_session(user)

    await log_audit(
        user_id=user["id"],
        user_name=user["name"],
        role=user["role"],
        action="login",
        module="auth",
        new_value={"email": user["email"], "role": user["role"]},
        ip_address=ip_address,
        operator_id=user.get("operator_id"),
    )

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


class ChangePasswordRequest(SanitizedModel):
    _unsanitized_fields = {"current_password", "new_password"}
    current_password: str
    new_password: str


class UpdateProfileRequest(SanitizedModel):
    name: str


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update the current user's display name."""
    name = sanitize_text(data.name)
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")

    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "name": name,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    updated_user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0})
    return UserResponse(
        id=updated_user["id"], email=updated_user["email"],
        name=updated_user["name"], phone=updated_user.get("phone"),
        role=updated_user["role"], operator_id=updated_user.get("operator_id"),
        status=updated_user.get("status", "active"),
        impersonated_by=updated_user.get("impersonated_by"),
        created_at=datetime.fromisoformat(updated_user["created_at"])
    )


@router.put("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change password for the currently logged-in user."""
    if not verify_password(data.current_password, current_user["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    new_hashed = hash_password(data.new_password)
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "password": new_hashed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "active_session_id": generate_id(),
        }}
    )
    return {"message": "Password changed successfully"}

class ForgotPasswordRequest(SanitizedModel):
    email: str
    method: str = "email"


class VerifyRecoveryOTPRequest(SanitizedModel):
    recovery_id: str
    otp: str


class ResetPasswordRequest(SanitizedModel):
    _unsanitized_fields = {"new_password"}
    recovery_id: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    """Step 1: Initiate password recovery. Send OTP via email."""
    if data.method != "email":
        raise HTTPException(status_code=400, detail="Password recovery OTP is available only via email.")
    user = await db.users.find_one({"email": data.email, "deleted_at": None}, {"_id": 0})
    otp = _generate_otp()
    now = datetime.now(timezone.utc)
    recovery_id = generate_id()
    email_masked = _mask_email(data.email)

    if not user:
        await db.password_recovery.delete_many({"email": data.email})
        await db.password_recovery.insert_one({
            "id": recovery_id,
            "user_id": None,
            "email": data.email,
            "phone": None,
            "otp": otp,
            "otp_attempts": 0,
            "otp_verified": False,
            "resend_count": 0,
            "method": data.method,
            "created_at": now.isoformat(),
            "last_sent_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=RECOVERY_OTP_EXPIRY_MINUTES)).isoformat(),
        })
        return {
            "recovery_id": recovery_id,
            "message": "If an account exists with this email, you will receive a recovery code.",
            "otp_sent": True,
            "method": data.method,
            "phone_last4": "",
            "email_masked": email_masked,
        }

    # Store recovery request
    recovery = {
        "id": recovery_id,
        "user_id": user["id"],
        "email": data.email,
        "phone": user.get("phone"),
        "otp": otp,
        "otp_attempts": 0,
        "otp_verified": False,
        "resend_count": 0,
        "method": data.method,
        "created_at": now.isoformat(),
        "last_sent_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=RECOVERY_OTP_EXPIRY_MINUTES)).isoformat(),
    }
    # Remove any existing recovery requests for this email
    await db.password_recovery.delete_many({"email": data.email})
    await db.password_recovery.insert_one(recovery)

    try:
        await _send_recovery_otp_email(data.email, otp)
        logger.info("Recovery OTP sent via email to %s", email_masked)
    except EmailServiceError as exc:
        await db.password_recovery.delete_one({"id": recovery_id})
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "recovery_id": recovery_id,
        "message": "Recovery code sent",
        "otp_sent": True,
        "method": "email",
        "phone_last4": "",
        "email_masked": email_masked,
    }


@router.post("/verify-recovery-otp")
async def verify_recovery_otp(data: VerifyRecoveryOTPRequest):
    """Step 2: Verify recovery OTP."""
    recovery = await db.password_recovery.find_one({"id": data.recovery_id}, {"_id": 0})
    if not recovery:
        raise HTTPException(status_code=400, detail="Recovery session not found or expired")

    # Check expiry
    expires_at = _parse_dt(recovery["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.password_recovery.delete_one({"id": data.recovery_id})
        raise HTTPException(status_code=400, detail="Recovery code has expired. Please try again.")

    # Check attempts
    if recovery.get("otp_attempts", 0) >= OTP_MAX_ATTEMPTS:
        await db.password_recovery.delete_one({"id": data.recovery_id})
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please try again.")

    if data.otp != recovery["otp"]:
        await db.password_recovery.update_one(
            {"id": data.recovery_id},
            {"$inc": {"otp_attempts": 1}}
        )
        remaining = OTP_MAX_ATTEMPTS - recovery.get("otp_attempts", 0) - 1
        raise HTTPException(status_code=400, detail=f"Invalid OTP. {remaining} attempts remaining.")

    # Mark OTP as verified
    await db.password_recovery.update_one(
        {"id": data.recovery_id},
        {"$set": {"otp_verified": True}}
    )

    return {
        "message": "OTP verified successfully",
        "recovery_id": data.recovery_id,
        "verified": True,
    }


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    """Step 3: Reset password after OTP verification."""
    recovery = await db.password_recovery.find_one({"id": data.recovery_id}, {"_id": 0})
    if not recovery:
        raise HTTPException(status_code=400, detail="Recovery session not found")

    if not recovery.get("otp_verified"):
        raise HTTPException(status_code=400, detail="OTP not verified")
    if not recovery.get("user_id"):
        await db.password_recovery.delete_one({"id": data.recovery_id})
        raise HTTPException(status_code=400, detail="Recovery session has expired")

    # Check expiry
    expires_at = _parse_dt(recovery["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.password_recovery.delete_one({"id": data.recovery_id})
        raise HTTPException(status_code=400, detail="Recovery session has expired")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Update password
    new_hashed = hash_password(data.new_password)
    await db.users.update_one(
        {"id": recovery["user_id"]},
        {"$set": {
            "password": new_hashed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "active_session_id": generate_id(),
        }}
    )

    # Delete recovery session
    await db.password_recovery.delete_one({"id": data.recovery_id})

    return {"message": "Password reset successfully. You can now login with your new password."}


@router.post("/resend-recovery-otp")
async def resend_recovery_otp(recovery_id: str = ""):
    """Resend recovery OTP."""
    recovery_id = sanitize_text(recovery_id)
    if not recovery_id:
        raise HTTPException(status_code=400, detail="Recovery ID is required")

    recovery = await db.password_recovery.find_one({"id": recovery_id}, {"_id": 0})
    if not recovery:
        raise HTTPException(status_code=400, detail="Recovery session not found")

    now = datetime.now(timezone.utc)
    _enforce_resend_limits(recovery, now)
    new_otp = _generate_otp()

    await db.password_recovery.update_one(
        {"id": recovery_id},
        {"$set": {
            "otp": new_otp,
            "otp_attempts": 0,
            "otp_verified": False,
            "last_sent_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=RECOVERY_OTP_EXPIRY_MINUTES)).isoformat(),
        }, "$inc": {"resend_count": 1}}
    )

    if not recovery.get("user_id"):
        return {
            "message": "Recovery code resent",
            "otp_sent": True,
            "email_masked": _mask_email(recovery["email"]),
        }
    try:
        await _send_recovery_otp_email(recovery["email"], new_otp)
        logger.info("Recovery OTP resent via email to %s", _mask_email(recovery["email"]))
    except EmailServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "message": "Recovery code resent",
        "otp_sent": True,
        "email_masked": _mask_email(recovery["email"]),
    }


@router.get("/app-state")
async def get_app_state(current_user: dict = Depends(get_current_user)):
    """Return platform maintenance/read-only state for the current user."""
    maintenance = await get_platform_maintenance_state()
    is_read_only = False
    if current_user["role"] in ["operator", "staff"] and current_user.get("operator_id"):
        access = await get_operator_access_state(current_user["operator_id"])
        is_read_only = access["is_read_only"]
        maintenance = {
            "maintenance_mode": access["maintenance_mode"],
            "maintenance_message": access["maintenance_message"],
        }

    return {
        "maintenance_mode": maintenance["maintenance_mode"],
        "maintenance_message": maintenance["maintenance_message"],
        "is_read_only": is_read_only,
        "role": current_user["role"],
    }
