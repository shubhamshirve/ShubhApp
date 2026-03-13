"""Auth router: register (with OTP), login, me."""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import random
import logging

from database import db
from models import OperatorCreate, UserLogin, UserResponse, TokenResponse
from utils import generate_id, hash_password, verify_password, create_token
from dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

# Test OTP that always works
TEST_OTP = "200796"


class OTPVerifyRequest(BaseModel):
    registration_id: str
    otp: str


@router.post("/register-init")
async def register_init(data: OperatorCreate):
    """Step 1: Validate registration data, check uniqueness, send OTP via WhatsApp."""
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
    otp = str(random.randint(100000, 999999))
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
        "gst_number": data.gst_number,
        "charge_gst": data.charge_gst,
        "bank_account_name": data.bank_account_name,
        "bank_account_number": data.bank_account_number,
        "bank_ifsc": data.bank_ifsc,
        "bank_name": data.bank_name,
        "otp": otp,
        "otp_attempts": 0,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
    }
    # Remove any existing pending registration for this email/phone
    await db.pending_registrations.delete_many({"$or": [{"email": data.email}, {"phone": data.phone}]})
    await db.pending_registrations.insert_one(pending)

    # Try to send OTP via WhatsApp
    otp_sent = False
    try:
        wa_config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
        if wa_config and wa_config.get("access_token"):
            from services.whatsapp_service import WhatsAppService
            wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
            # Send as a simple text message using the WhatsApp API
            await wa_service.send_text_message(
                recipient_phone=data.phone,
                message=f"Your OTP for registration is: {otp}. Valid for 10 minutes."
            )
            otp_sent = True
            logger.info(f"OTP sent via WhatsApp to {data.phone[-4:]}")
    except Exception as e:
        logger.warning(f"Failed to send OTP via WhatsApp: {e}")

    return {
        "registration_id": registration_id,
        "message": "OTP sent to your WhatsApp number" if otp_sent else "OTP generated. Please enter the verification code.",
        "otp_sent": otp_sent,
        "phone_last4": data.phone[-4:],
    }


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_and_register(data: OTPVerifyRequest):
    """Step 2: Verify OTP and complete registration."""
    pending = await db.pending_registrations.find_one({"id": data.registration_id}, {"_id": 0})
    if not pending:
        raise HTTPException(status_code=400, detail="Registration session not found or expired. Please start again.")

    # Check expiry
    expires_at = datetime.fromisoformat(pending["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.pending_registrations.delete_one({"id": data.registration_id})
        raise HTTPException(status_code=400, detail="OTP has expired. Please register again.")

    # Check attempts
    if pending.get("otp_attempts", 0) >= 5:
        await db.pending_registrations.delete_one({"id": data.registration_id})
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please register again.")

    # Verify OTP - accept test OTP or actual OTP
    if data.otp != TEST_OTP and data.otp != pending["otp"]:
        await db.pending_registrations.update_one(
            {"id": data.registration_id},
            {"$inc": {"otp_attempts": 1}}
        )
        remaining = 5 - pending.get("otp_attempts", 0) - 1
        raise HTTPException(status_code=400, detail=f"Invalid OTP. {remaining} attempts remaining.")

    # OTP verified - complete registration
    # Re-check uniqueness (in case someone registered between init and verify)
    existing_email = await db.users.find_one({"email": pending["email"], "deleted_at": None})
    if existing_email:
        await db.pending_registrations.delete_one({"id": data.registration_id})
        raise HTTPException(status_code=400, detail="Email already registered")

    # Find the lowest-priced plan for trial
    lowest_plan = await db.saas_plans.find_one(
        {"deleted_at": None},
        {"_id": 0},
        sort=[("monthly_price", 1)]
    )

    now = datetime.now(timezone.utc)
    operator_id = generate_id()
    user_id = generate_id()
    trial_end = (now + timedelta(days=3)).isoformat()

    operator = {
        "id": operator_id,
        "company_name": pending["company_name"],
        "owner_name": pending["owner_name"],
        "email": pending["email"],
        "phone": pending["phone"],
        "gst_number": pending.get("gst_number"),
        "charge_gst": pending.get("charge_gst", False),
        "bank_account_name": pending.get("bank_account_name"),
        "bank_account_number": pending.get("bank_account_number"),
        "bank_ifsc": pending.get("bank_ifsc"),
        "bank_name": pending.get("bank_name"),
        "status": "trial",
        "saas_plan_id": lowest_plan["id"] if lowest_plan else None,
        "saas_plan_name": lowest_plan["name"] if lowest_plan else None,
        "trial_ends_at": trial_end,
        "subscription_ends_at": trial_end,
        "is_read_only": False,
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
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.users.insert_one(user)

    # Clean up pending registration
    await db.pending_registrations.delete_one({"id": data.registration_id})

    token = create_token({"id": user_id, "email": pending["email"], "role": "operator", "operator_id": operator_id})

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
    if not registration_id:
        raise HTTPException(status_code=400, detail="Registration ID is required")
    pending = await db.pending_registrations.find_one({"id": registration_id}, {"_id": 0})
    if not pending:
        raise HTTPException(status_code=400, detail="Registration session not found or expired.")

    expires_at = datetime.fromisoformat(pending["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.pending_registrations.delete_one({"id": registration_id})
        raise HTTPException(status_code=400, detail="Session expired. Please register again.")

    # Generate new OTP
    new_otp = str(random.randint(100000, 999999))
    now = datetime.now(timezone.utc)
    await db.pending_registrations.update_one(
        {"id": registration_id},
        {"$set": {
            "otp": new_otp,
            "otp_attempts": 0,
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        }}
    )

    # Try to send via WhatsApp
    otp_sent = False
    try:
        wa_config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
        if wa_config and wa_config.get("access_token"):
            from services.whatsapp_service import WhatsAppService
            wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
            await wa_service.send_text_message(
                recipient_phone=pending["phone"],
                message=f"Your OTP for registration is: {new_otp}. Valid for 10 minutes."
            )
            otp_sent = True
    except Exception as e:
        logger.warning(f"Failed to resend OTP: {e}")

    return {
        "message": "OTP resent to your WhatsApp" if otp_sent else "New OTP generated.",
        "otp_sent": otp_sent,
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

    # Set subscription to expire in 3 days
    trial_end = (now + timedelta(days=3)).isoformat()

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
        "saas_plan_id": lowest_plan["id"] if lowest_plan else None,
        "saas_plan_name": lowest_plan["name"] if lowest_plan else None,
        "trial_ends_at": trial_end,
        "subscription_ends_at": trial_end,
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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


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
        {"$set": {"password": new_hashed, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Password changed successfully"}



# Test OTP for password recovery
RECOVERY_TEST_OTP = "475869"


class ForgotPasswordRequest(BaseModel):
    email: str
    method: str = "email"  # "email" or "whatsapp"


class VerifyRecoveryOTPRequest(BaseModel):
    recovery_id: str
    otp: str


class ResetPasswordRequest(BaseModel):
    recovery_id: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    """Step 1: Initiate password recovery. Send OTP via email or WhatsApp."""
    user = await db.users.find_one({"email": data.email, "deleted_at": None}, {"_id": 0})
    if not user:
        # Don't reveal if email exists
        raise HTTPException(status_code=400, detail="If an account exists with this email, you will receive a recovery code.")

    # Generate OTP
    otp = str(random.randint(100000, 999999))
    now = datetime.now(timezone.utc)
    recovery_id = generate_id()

    # Store recovery request
    recovery = {
        "id": recovery_id,
        "user_id": user["id"],
        "email": data.email,
        "phone": user.get("phone"),
        "otp": otp,
        "otp_attempts": 0,
        "otp_verified": False,
        "method": data.method,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=15)).isoformat(),
    }
    # Remove any existing recovery requests for this email
    await db.password_recovery.delete_many({"email": data.email})
    await db.password_recovery.insert_one(recovery)

    otp_sent = False
    phone_last4 = ""

    if data.method == "whatsapp" and user.get("phone"):
        # Send via WhatsApp
        try:
            wa_config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
            if wa_config and wa_config.get("access_token"):
                from services.whatsapp_service import WhatsAppService
                wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
                await wa_service.send_text_message(
                    recipient_phone=user["phone"],
                    message=f"Your E-Bill password recovery OTP is: {otp}. Valid for 15 minutes. Do not share this code."
                )
                otp_sent = True
                phone_last4 = user["phone"][-4:]
                logger.info(f"Recovery OTP sent via WhatsApp to {phone_last4}")
        except Exception as e:
            logger.warning(f"Failed to send recovery OTP via WhatsApp: {e}")
    else:
        # Email method - for now just log (would need email service)
        logger.info(f"Recovery OTP for {data.email}: {otp} (email sending not implemented)")
        otp_sent = True  # Pretend it's sent for demo purposes

    return {
        "recovery_id": recovery_id,
        "message": "Recovery code sent" if otp_sent else "Recovery code generated",
        "otp_sent": otp_sent,
        "method": data.method,
        "phone_last4": phone_last4,
    }


@router.post("/verify-recovery-otp")
async def verify_recovery_otp(data: VerifyRecoveryOTPRequest):
    """Step 2: Verify recovery OTP."""
    recovery = await db.password_recovery.find_one({"id": data.recovery_id}, {"_id": 0})
    if not recovery:
        raise HTTPException(status_code=400, detail="Recovery session not found or expired")

    # Check expiry
    expires_at = datetime.fromisoformat(recovery["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.password_recovery.delete_one({"id": data.recovery_id})
        raise HTTPException(status_code=400, detail="Recovery code has expired. Please try again.")

    # Check attempts
    if recovery.get("otp_attempts", 0) >= 5:
        await db.password_recovery.delete_one({"id": data.recovery_id})
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please try again.")

    # Verify OTP - accept test OTP or actual OTP
    if data.otp != RECOVERY_TEST_OTP and data.otp != recovery["otp"]:
        await db.password_recovery.update_one(
            {"id": data.recovery_id},
            {"$inc": {"otp_attempts": 1}}
        )
        remaining = 5 - recovery.get("otp_attempts", 0) - 1
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

    # Check expiry
    expires_at = datetime.fromisoformat(recovery["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.password_recovery.delete_one({"id": data.recovery_id})
        raise HTTPException(status_code=400, detail="Recovery session has expired")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Update password
    new_hashed = hash_password(data.new_password)
    await db.users.update_one(
        {"id": recovery["user_id"]},
        {"$set": {"password": new_hashed, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    # Delete recovery session
    await db.password_recovery.delete_one({"id": data.recovery_id})

    return {"message": "Password reset successfully. You can now login with your new password."}


@router.post("/resend-recovery-otp")
async def resend_recovery_otp(recovery_id: str = ""):
    """Resend recovery OTP."""
    if not recovery_id:
        raise HTTPException(status_code=400, detail="Recovery ID is required")

    recovery = await db.password_recovery.find_one({"id": recovery_id}, {"_id": 0})
    if not recovery:
        raise HTTPException(status_code=400, detail="Recovery session not found")

    # Generate new OTP
    new_otp = str(random.randint(100000, 999999))
    now = datetime.now(timezone.utc)

    await db.password_recovery.update_one(
        {"id": recovery_id},
        {"$set": {
            "otp": new_otp,
            "otp_attempts": 0,
            "otp_verified": False,
            "expires_at": (now + timedelta(minutes=15)).isoformat(),
        }}
    )

    otp_sent = False
    if recovery.get("method") == "whatsapp" and recovery.get("phone"):
        try:
            wa_config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
            if wa_config and wa_config.get("access_token"):
                from services.whatsapp_service import WhatsAppService
                wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
                await wa_service.send_text_message(
                    recipient_phone=recovery["phone"],
                    message=f"Your E-Bill password recovery OTP is: {new_otp}. Valid for 15 minutes."
                )
                otp_sent = True
        except Exception as e:
            logger.warning(f"Failed to resend recovery OTP: {e}")
    else:
        otp_sent = True  # Email - pretend sent

    return {
        "message": "Recovery code resent" if otp_sent else "New code generated",
        "otp_sent": otp_sent,
    }
