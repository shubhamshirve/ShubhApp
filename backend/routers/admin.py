"""Admin: SaaS Plans, Operators, Settings, Gateways, Addons, Dashboard, Audit, Cron, Reports."""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Request, Response
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import os
import uuid

from database import db
from models import (
    SaaSPlanCreate, SaaSPlanResponse,
    OperatorResponse, OperatorUpdate, AdminOperatorCreate, ExtendSubscriptionRequest,
    GlobalSettingsUpdate, AdminPaymentGatewayConfig,
    AddonCreate, AuditLogResponse,
    WhatsAppConfig, WhatsAppTemplateSettings, WhatsAppTestMessage,
    WhatsAppTemplateTestRequest, SystemResetOTPRequest,
    DiscountCodeCreate, DiscountCodeResponse,
    WhatsAppTemplateCreate, WhatsAppTemplateUpdate,
    ReminderSettingsUpdate, EmailSettingsUpdate, EmailTestRequest,
    SecuritySettingsUpdate, SecuritySettingsResponse,
    EnvSettingsUpdate, AdminEnvSettingsResponse,
)
from utils import generate_id, hash_password, create_token, generate_unique_referral_code
from dependencies import require_admin, get_current_user
from audit import log_audit
from sanitization import SanitizedModel, sanitize_filename
from services.global_settings_store import get_global_settings_doc, save_global_settings_doc
from services.scheduler_settings import DEFAULT_CRON_SCHEDULES, merge_cron_schedule_settings, split_cron_time
from services.email_service import EmailServiceError, get_email_providers_async
from routers.wallet import get_or_create_wallet, credit_wallet

router = APIRouter(prefix="/admin", tags=["Admin"])

# Upload directory for logos
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _parse_operator(o: dict) -> OperatorResponse:
    return OperatorResponse(**{
        **o,
        "created_at": datetime.fromisoformat(o["created_at"]),
        "trial_ends_at": datetime.fromisoformat(o["trial_ends_at"]) if o.get("trial_ends_at") else None,
        "subscription_ends_at": datetime.fromisoformat(o["subscription_ends_at"]) if o.get("subscription_ends_at") else None,
    })


def _reschedule_platform_jobs(scheduler, settings: dict):
    if not scheduler:
        return
    schedule = merge_cron_schedule_settings(settings)
    job_map = {
        "daily_backup": schedule["cron_backup_time"],
        "daily_expiry": schedule["cron_expiry_time"],
        "daily_invoices": schedule["cron_invoice_time"],
        "daily_wallet_check": schedule["cron_wallet_time"],
        "daily_reminders": schedule["cron_reminder_time"],
        "daily_operator_report": schedule.get("cron_daily_report_time", "09:30"),
    }
    for job_id, time_value in job_map.items():
        hour, minute = split_cron_time(time_value)
        try:
            # IMPORTANT: Must pass timezone explicitly — reschedule_job defaults to UTC,
            # not the scheduler's Asia/Kolkata timezone.
            scheduler.reschedule_job(
                job_id,
                trigger="cron",
                hour=hour,
                minute=minute,
                timezone="Asia/Kolkata",
            )
        except Exception:
            pass  # Job may not be registered yet


async def _send_email_settings_test(
    *,
    provider_key: str,
    to_email: str,
    current_user: dict,
):
    providers = await get_email_providers_async()
    provider = providers.get(provider_key)
    if not provider:
        if provider_key == "primary":
            raise HTTPException(status_code=400, detail="Resend is not configured. Please save Resend settings first.")
        raise HTTPException(status_code=400, detail="SMTP fallback is not configured. Please save SMTP settings first.")

    try:
        result = await provider.send_email(
            to_email=to_email,
            subject=f"E-Bill {('Resend' if provider_key == 'primary' else 'SMTP')} test email",
            text=(
                "This is a test email from E-Bill admin settings. "
                f"It was sent using {'Resend' if provider_key == 'primary' else 'SMTP fallback'}."
            ),
            html=(
                "<p>This is a test email from <strong>E-Bill</strong> admin settings.</p>"
                f"<p>Provider used: <strong>{'Resend' if provider_key == 'primary' else 'SMTP fallback'}</strong>.</p>"
                f"<p>Requested by: <strong>{current_user.get('name', 'Admin')}</strong>.</p>"
            ),
        )
    except EmailServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "test", "email_settings", None,
        {
            "provider": "resend" if provider_key == "primary" else "smtp",
            "to_email": to_email,
        },
        ip_address=current_user.get("_ip_address")
    )
    return {
        "message": f"Test email sent successfully via {'Resend' if provider_key == 'primary' else 'SMTP fallback'}",
        "provider": result.get("provider", "unknown"),
    }


# ─── SaaS Plans ──────────────────────────────────────────────────────────────

@router.post("/saas-plans", response_model=SaaSPlanResponse)
async def create_saas_plan(data: SaaSPlanCreate, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    plan = {
        "id": generate_id(), "name": data.name,
        "monthly_price": data.monthly_price,
        "per_invoice_price": data.per_invoice_price,
        "max_subscribers": data.max_subscribers,
        "max_staff": data.max_staff,
        "included_addons": data.included_addons,
        "gst_applicable": False,  # GST inclusive pricing
        "trial_enabled": False, "trial_days": 0,
        "status": "active", "created_at": now.isoformat(),
        "updated_at": now.isoformat(), "deleted_at": None,
    }
    await db.saas_plans.insert_one(plan)
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                    "create", "saas_plans", None, {"name": data.name, "monthly_price": data.monthly_price},
                    ip_address=current_user.get("_ip_address"))
    return SaaSPlanResponse(**{**plan, "created_at": now})


@router.get("/saas-plans", response_model=List[SaaSPlanResponse])
async def get_saas_plans(current_user: dict = Depends(require_admin)):
    plans = await db.saas_plans.find({"deleted_at": None}, {"_id": 0}).to_list(100)
    return [SaaSPlanResponse(**{**p, "created_at": datetime.fromisoformat(p["created_at"])}) for p in plans]


@router.put("/saas-plans/{plan_id}", response_model=SaaSPlanResponse)
async def update_saas_plan(plan_id: str, data: SaaSPlanCreate, current_user: dict = Depends(require_admin)):
    existing = await db.saas_plans.find_one({"id": plan_id, "deleted_at": None}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found")
    now = datetime.now(timezone.utc)
    update_data = {
        "name": data.name,
        "monthly_price": data.monthly_price,
        "per_invoice_price": data.per_invoice_price,
        "max_subscribers": data.max_subscribers,
        "max_staff": data.max_staff,
        "included_addons": data.included_addons,
        "gst_applicable": False,
        "updated_at": now.isoformat(),
    }
    await db.saas_plans.update_one({"id": plan_id}, {"$set": update_data})
    updated = await db.saas_plans.find_one({"id": plan_id}, {"_id": 0})
    return SaaSPlanResponse(**{**updated, "created_at": datetime.fromisoformat(updated["created_at"])})


@router.delete("/saas-plans/{plan_id}")
async def delete_saas_plan(plan_id: str, current_user: dict = Depends(require_admin)):
    result = await db.saas_plans.update_one(
        {"id": plan_id, "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Plan deleted successfully"}


# ─── Operators ───────────────────────────────────────────────────────────────

@router.get("/operators", response_model=List[OperatorResponse])
async def get_operators(current_user: dict = Depends(require_admin)):
    ops = await db.operators.find({"deleted_at": None}, {"_id": 0}).to_list(1000)
    result = []
    for o in ops:
        subscriber_count = await db.subscribers.count_documents(
            {"operator_id": o["id"], "deleted_at": None}
        )
        o["subscriber_count"] = subscriber_count
        result.append(_parse_operator(o))
    return result


@router.get("/operators/{operator_id}", response_model=OperatorResponse)
async def get_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    op = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")
    return _parse_operator(op)


@router.put("/operators/{operator_id}", response_model=OperatorResponse)
async def update_operator(operator_id: str, data: OperatorUpdate, current_user: dict = Depends(require_admin)):
    existing = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Operator not found")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.operators.update_one({"id": operator_id}, {"$set": update_data})
    updated = await db.operators.find_one({"id": operator_id}, {"_id": 0})
    return _parse_operator(updated)


@router.post("/operators/create", response_model=OperatorResponse)
async def create_operator_manually(data: AdminOperatorCreate, current_user: dict = Depends(require_admin)):
    """Manually create operator — no trial, direct plan assignment."""
    existing = await db.users.find_one({"email": data.email, "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    plan = await db.saas_plans.find_one({"id": data.saas_plan_id, "deleted_at": None}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="SaaS plan not found")

    now = datetime.now(timezone.utc)
    operator_id = generate_id()
    user_id = generate_id()
    subscription_ends_at = (now + timedelta(days=30 * data.subscription_months)).isoformat()
    referral_code = await generate_unique_referral_code(db)

    operator = {
        "id": operator_id, "company_name": data.company_name, "owner_name": data.owner_name,
        "email": data.email, "phone": data.phone, "business_type": data.business_type,
        "gst_number": data.gst_number, "pan_number": data.pan_number, "address": data.address,
        "charge_gst": data.charge_gst, "bank_account_name": data.bank_account_name,
        "bank_account_number": data.bank_account_number, "bank_ifsc": data.bank_ifsc,
        "bank_name": data.bank_name, "status": data.status, "saas_plan_id": data.saas_plan_id,
        "saas_plan_name": plan["name"], "trial_ends_at": None,
        "subscription_ends_at": subscription_ends_at if data.status == "active" else None,
        "referral_code": referral_code,
        "referred_by_code": None,
        "referral_discount_eligible": False,
        "referral_discount_used": False,
        "is_read_only": False, "created_at": now.isoformat(),
        "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.operators.insert_one(operator)

    # Initialize wallet according to plan amount (monthly_price)
    await get_or_create_wallet(operator_id)
    if plan.get("monthly_price", 0) > 0:
        await credit_wallet(
            operator_id=operator_id,
            amount=plan["monthly_price"],
            description=f"Initial balance from {plan['name']} plan",
            tx_type="admin_credit"
        )

    user = {
        "id": user_id, "email": data.email, "name": data.owner_name, "phone": data.phone,
        "password": hash_password(data.password), "role": "operator",
        "operator_id": operator_id, "status": "active",
        "active_session_id": generate_id(),
        "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.users.insert_one(user)

    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "create", "operators", None,
        {"company_name": data.company_name, "email": data.email, "plan": plan["name"]},
        ip_address=current_user.get("_ip_address")
    )
    return OperatorResponse(**{
        **operator, "created_at": now, "trial_ends_at": None,
        "subscription_ends_at": datetime.fromisoformat(subscription_ends_at) if data.status == "active" else None
    })


@router.post("/operators/{operator_id}/extend-subscription")
async def extend_operator_subscription(
    operator_id: str, data: ExtendSubscriptionRequest,
    current_user: dict = Depends(require_admin)
):
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    now = datetime.now(timezone.utc)
    if data.custom_date:
        new_expiry = data.custom_date
    elif data.months:
        current_expiry = operator.get("subscription_ends_at")
        base_date = now
        if current_expiry:
            base_date = datetime.fromisoformat(current_expiry)
            if base_date < now:
                base_date = now
        new_expiry = (base_date + timedelta(days=30 * data.months)).isoformat()
    else:
        raise HTTPException(status_code=400, detail="Either months or custom_date must be provided")

    await db.operators.update_one(
        {"id": operator_id},
        {"$set": {"subscription_ends_at": new_expiry, "status": "active",
                  "is_read_only": False, "updated_at": now.isoformat()}}
    )
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "extend_subscription", "operators",
        {"old_expiry": operator.get("subscription_ends_at")},
        {"new_expiry": new_expiry, "months": data.months},
        ip_address=current_user.get("_ip_address")
    )
    return {"message": "Subscription extended successfully", "new_expiry_date": new_expiry, "operator_id": operator_id}


@router.delete("/operators/{operator_id}")
async def delete_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    now = datetime.now(timezone.utc)
    deleted_at = now.isoformat()

    # ── Soft-delete relational records ─────────────────────────────────────
    await db.operators.update_one({"id": operator_id}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})
    await db.users.update_many({"operator_id": operator_id, "deleted_at": None}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})
    await db.subscribers.update_many({"operator_id": operator_id, "deleted_at": None}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})
    await db.operator_plans.update_many({"operator_id": operator_id, "deleted_at": None}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})
    await db.invoices.update_many({"operator_id": operator_id, "deleted_at": None}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})

    # ── Hard-delete config & wallet data ───────────────────────────────────
    await db.operator_wallets.delete_many({"operator_id": operator_id})
    await db.wallet_transactions.delete_many({"operator_id": operator_id})
    await db.payment_gateways.delete_many({"operator_id": operator_id})
    await db.invoice_settings.delete_many({"operator_id": operator_id})
    await db.operator_theme.delete_many({"operator_id": operator_id})
    await db.notification_queue.delete_many({"operator_id": operator_id})
    await db.checkout_orders.delete_many({"operator_id": operator_id})
    await db.whatsapp_message_logs.delete_many({"operator_id": operator_id})
    await db.announcements.delete_many({"operator_id": operator_id})
    await db.saas_payments.delete_many({"operator_id": operator_id})

    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "delete", "operators",
        {"company_name": operator["company_name"], "email": operator["email"]},
        {"deleted_at": deleted_at},
        ip_address=current_user.get("_ip_address")
    )
    return {"message": "Operator and all related data deleted successfully",
            "operator_id": operator_id, "company_name": operator["company_name"]}


@router.post("/operators/{operator_id}/assign-plan")
async def assign_plan_to_operator(
    operator_id: str, plan_id: str = Query(...), current_user: dict = Depends(require_admin)
):
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    plan = await db.saas_plans.find_one({"id": plan_id, "deleted_at": None}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    now = datetime.now(timezone.utc)
    await db.operators.update_one({"id": operator_id}, {"$set": {
        "saas_plan_id": plan_id, "saas_plan_name": plan["name"],
        "status": "active",
        "subscription_ends_at": (now + timedelta(days=30)).isoformat(),
        "is_read_only": False, "updated_at": now.isoformat()
    }})
    return {"message": "Plan assigned successfully"}


@router.post("/operators/{operator_id}/suspend")
async def suspend_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    result = await db.operators.update_one(
        {"id": operator_id, "deleted_at": None},
        {"$set": {"status": "suspended", "is_read_only": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Operator not found")
    return {"message": "Operator suspended"}


@router.post("/operators/{operator_id}/activate")
async def activate_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    result = await db.operators.update_one(
        {"id": operator_id, "deleted_at": None},
        {"$set": {"status": "active", "is_read_only": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Operator not found")
    return {"message": "Operator activated"}


@router.post("/operators/{operator_id}/impersonate")
async def impersonate_operator(operator_id: str, response: Response, current_user: dict = Depends(require_admin)):
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    user = await db.users.find_one({"operator_id": operator_id, "role": "operator", "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Operator user not found")
        
    settings = await db.global_settings.find_one({"type": "platform"}) or {}
    timeout = float(settings.get("session_timeout_hours", 24.0))
    token = create_token({
        "id": user["id"], "email": user["email"], "role": "operator",
        "operator_id": operator_id, "impersonated_by": current_user["id"]
    }, expiration_hours=timeout)
    
    # Set httpOnly cookie for impersonation
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(timeout * 3600),
        path="/"
    )
    
    return {
        "access_token": token, "token_type": "bearer",
        "operator": {"id": operator_id, "company_name": operator["company_name"], "owner_name": operator.get("owner_name", "")}
    }


@router.post("/return-from-impersonate")
async def return_from_impersonate(response: Response, current_user: dict = Depends(get_current_user)):
    impersonated_by = current_user.get("impersonated_by")
    if not impersonated_by:
        raise HTTPException(status_code=400, detail="Not impersonating any operator")
    admin_user = await db.users.find_one({"id": impersonated_by, "role": "admin", "deleted_at": None}, {"_id": 0})
    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin user not found")
        
    settings = await db.global_settings.find_one({"type": "platform"}) or {}
    timeout = float(settings.get("session_timeout_hours", 24.0))
    session_id = generate_id()
    await db.users.update_one(
        {"id": admin_user["id"]},
        {"$set": {"active_session_id": session_id, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    token = create_token(
        {"id": admin_user["id"], "email": admin_user["email"], "role": "admin", "session_id": session_id},
        expiration_hours=timeout,
    )
    
    # Set httpOnly cookie for admin return
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(timeout * 3600),
        path="/"
    )
    
    return {"access_token": token, "token_type": "bearer"}


class AdminChangePasswordRequest(SanitizedModel):
    _unsanitized_fields = {"new_password"}
    new_password: str


@router.put("/operators/{operator_id}/change-password")
async def admin_change_operator_password(
    operator_id: str,
    data: AdminChangePasswordRequest,
    current_user: dict = Depends(require_admin)
):
    """Admin can reset an operator's password."""
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    user = await db.users.find_one({"operator_id": operator_id, "role": "operator", "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Operator user account not found")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    new_hashed = hash_password(data.new_password)
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "password": new_hashed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "active_session_id": generate_id(),
        }}
    )

    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "password_reset", "operator", operator_id, {"operator_name": operator.get("company_name")},
        ip_address=current_user.get("_ip_address")
    )

    return {"message": f"Password changed successfully for {operator.get('company_name')}"}


# ─── Addons ──────────────────────────────────────────────────────────────────

@router.post("/addons")
async def create_addon(data: AddonCreate, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    addon = {
        "id": generate_id(), "name": data.name, "code": data.code,
        "price": data.price, "description": data.description,
        "status": "active", "created_at": now.isoformat(), "deleted_at": None
    }
    await db.addons.insert_one(addon)
    addon.pop("_id", None)
    return addon


@router.get("/addons")
async def get_addons(current_user: dict = Depends(require_admin)):
    addons = await db.addons.find({"deleted_at": None}, {"_id": 0}).to_list(100)
    return addons


@router.put("/addons/{addon_id}")
async def update_addon(addon_id: str, data: AddonCreate, current_user: dict = Depends(require_admin)):
    existing = await db.addons.find_one({"id": addon_id, "deleted_at": None}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Addon not found")
    now = datetime.now(timezone.utc)
    await db.addons.update_one({"id": addon_id}, {"$set": {
        "name": data.name, "price": data.price,
        "description": data.description, "updated_at": now.isoformat()
    }})
    updated = await db.addons.find_one({"id": addon_id}, {"_id": 0})
    return updated


@router.delete("/addons/{addon_id}")
async def delete_addon(addon_id: str, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    result = await db.addons.update_one(
        {"id": addon_id, "deleted_at": None},
        {"$set": {"deleted_at": now.isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Addon not found")
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                    "delete", "addons", {"addon_id": addon_id}, {},
                    ip_address=current_user.get("_ip_address"))
    return {"message": "Addon deleted"}


@router.post("/operators/{operator_id}/addons/{addon_code}")
async def assign_addon_to_operator(
    operator_id: str, addon_code: str, current_user: dict = Depends(require_admin)
):
    addon = await db.addons.find_one({"code": addon_code, "deleted_at": None}, {"_id": 0})
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    now = datetime.now(timezone.utc)
    existing_addons = operator.get("active_addons") or []
    if addon_code not in existing_addons:
        existing_addons.append(addon_code)
    # Set addon expiry = operator's current subscription_ends_at
    addon_expiry = operator.get("addon_expiry") or {}
    expiry_date = operator.get("subscription_ends_at") or now.isoformat()
    addon_expiry[addon_code] = expiry_date
    update_fields = {"active_addons": existing_addons, "addon_expiry": addon_expiry, "updated_at": now.isoformat()}
    # When staff_management addon is assigned, set max_staff override to 5
    if addon_code == "staff_management":
        update_fields["max_staff"] = 5
    await db.operators.update_one(
        {"id": operator_id},
        {"$set": update_fields}
    )
    return {"message": f"Addon '{addon['name']}' assigned to operator"}


# ─── Settings ────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_global_settings(current_user: dict = Depends(require_admin)):
    settings = await get_global_settings_doc({"type": "platform"}, {"_id": 0})
    if not settings:
        return {
            "active_payment_gateway": "razorpay", "notification_enabled": True,
            "auto_invoice_days_before": 3, "late_fee_percentage": 0, "gst_rate": 18,
            "gst_enabled_on_saas_plans": True,
            "gst_enabled_on_wallet_topup": True,
            "referral_discount_percent": 10,
            "referral_discount_max_amount": 500,
            "referral_reward_percent": 5,
            "referral_reward_valid_days": 90,
            "maintenance_mode": False,
            "maintenance_message": "The app is under maintenance. Updates and automation are temporarily paused.",
            "session_timeout_hours": 24.0,
            "welcome_modal_enabled": False,
            "welcome_modal_title": "Welcome to E-Bill",
            "welcome_modal_content": None,
            "welcome_modal_show_for": "all",
            "welcome_modal_version": 1,
            "cron_daily_report_time": "09:30",
            **DEFAULT_CRON_SCHEDULES,
        }
    return {
        "gst_enabled_on_saas_plans": True,
        "gst_enabled_on_wallet_topup": True,
        **settings,
        **merge_cron_schedule_settings(settings),
    }


@router.get("/welcome-modal")
async def get_welcome_modal(current_user: dict = Depends(get_current_user)):
    """Return welcome modal settings — accessible to all authenticated roles."""
    settings = await get_global_settings_doc({"type": "platform"}, {"_id": 0}) or {}
    return {
        "enabled": bool(settings.get("welcome_modal_enabled", False)),
        "title": settings.get("welcome_modal_title") or "Welcome to E-Bill",
        "content": settings.get("welcome_modal_content") or "",
        "show_for": settings.get("welcome_modal_show_for") or "all",
        "version": int(settings.get("welcome_modal_version") or 1),
    }


@router.put("/settings")
async def update_global_settings(
    data: GlobalSettingsUpdate,
    request: Request,
    current_user: dict = Depends(require_admin)
):
    now = datetime.now(timezone.utc)
    old_settings = await get_global_settings_doc({"type": "platform"}, {"_id": 0}) or {}
    normalized_schedule = merge_cron_schedule_settings(data.model_dump())
    settings = {
        "type": "platform",
        **data.model_dump(),
        **normalized_schedule,
        "updated_at": now.isoformat(),
        "updated_by": current_user["id"],
    }
    await save_global_settings_doc({"type": "platform"}, settings)
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler:
        _reschedule_platform_jobs(scheduler, settings)
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                    "update", "global_settings", old_settings, data.model_dump(),
                    ip_address=current_user.get("_ip_address"))
    return {"message": "Settings updated successfully"}


# ─── Global Reminder Settings ─────────────────────────────────────────────────

VALID_BEFORE_DAYS = [1, 2, 3, 5, 7]
VALID_AFTER_DAYS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
DEFAULT_REMINDER_SETTINGS = {
    "enabled": True,
    "remind_before_due": [7, 5, 3, 2, 1],
    "remind_on_due": True,
    "remind_after_due": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "max_reminders_per_invoice": 20,
}


@router.get("/reminder-settings")
async def get_global_reminder_settings(current_user: dict = Depends(require_admin)):
    """Get platform-wide payment reminder automation settings."""
    doc = await db.global_settings.find_one({"type": "reminder_settings"}, {"_id": 0})
    if not doc:
        return DEFAULT_REMINDER_SETTINGS
    return {k: v for k, v in doc.items() if k not in ("type", "_id", "updated_at", "updated_by")}


@router.put("/reminder-settings")
async def update_global_reminder_settings(
    data: ReminderSettingsUpdate,
    current_user: dict = Depends(require_admin),
):
    """Update platform-wide payment reminder automation settings."""
    for d in data.remind_before_due:
        if d not in VALID_BEFORE_DAYS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid remind_before_due day: {d}. Allowed: {VALID_BEFORE_DAYS}"
            )
    for d in data.remind_after_due:
        if d not in VALID_AFTER_DAYS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid remind_after_due day: {d}. Allowed: {VALID_AFTER_DAYS}"
            )

    now = datetime.now(timezone.utc).isoformat()
    update_doc = {
        "type": "reminder_settings",
        "enabled": data.enabled,
        "remind_before_due": sorted(set(data.remind_before_due), reverse=True),
        "remind_on_due": data.remind_on_due,
        "remind_after_due": sorted(set(data.remind_after_due)),
        "max_reminders_per_invoice": max(1, min(data.max_reminders_per_invoice, 20)),
        "updated_at": now,
        "updated_by": current_user["id"],
    }

    await db.global_settings.update_one(
        {"type": "reminder_settings"},
        {"$set": update_doc},
        upsert=True,
    )

    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "update", "global_reminder_settings", None, update_doc,
        ip_address=current_user.get("_ip_address"),
    )

    return {**update_doc, "message": "Global reminder settings updated successfully"}

# ─── Platform WhatsApp Config ─────────────────────────────────────────────────

@router.get("/whatsapp-config")
async def get_platform_whatsapp_config(current_user: dict = Depends(require_admin)):
    config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
    if not config:
        return {"phone_number_id": "", "access_token_preview": "", "business_account_id": "", "webhook_verify_token_preview": "", "is_configured": False}
    # Mask the access_token for display
    token = config.get("access_token", "")
    masked_token = token[:8] + "****" if len(token) > 8 else ("****" if token else "")
    verify_token = config.get("webhook_verify_token", "")
    masked_verify = verify_token[:4] + "****" if len(verify_token) > 4 else ("****" if verify_token else "")
    return {
        "phone_number_id": config.get("phone_number_id", ""),
        "access_token_preview": masked_token,
        "business_account_id": config.get("business_account_id", ""),
        "webhook_verify_token_preview": masked_verify,
        "is_configured": bool(token)
    }


@router.get("/whatsapp-diagnostics")
async def get_whatsapp_diagnostics(current_user: dict = Depends(require_admin)):
    """
    Fetch live account diagnostics from Meta WhatsApp API.
    Returns phone number status, throughput (live vs development mode), and WABA details.
    """
    from services.whatsapp_service import WhatsAppService
    config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
    if not config or not config.get("access_token") or not config.get("phone_number_id"):
        raise HTTPException(status_code=400, detail="WhatsApp is not configured yet.")
    wa = WhatsAppService(config["phone_number_id"], config["access_token"])
    result = {}

    # Phone number details
    phone_status = await wa.check_account_status()
    result["phone_number"] = phone_status

    # WABA details (if business_account_id configured)
    waba_id = config.get("business_account_id", "")
    if waba_id:
        waba_status = await wa.check_waba_status(waba_id)
        result["waba"] = waba_status
    else:
        result["waba"] = {"note": "business_account_id not configured"}

    # Determine mode
    throughput = (phone_status.get("throughput") or {}).get("level", "")
    display_phone = phone_status.get("display_phone_number", "")

    # Meta's test/demo phone numbers use the US +1 555-xxx-xxxx range
    is_test_number = "555" in display_phone.replace(" ", "").replace("-", "")

    result["mode"] = "LIVE" if (throughput == "STANDARD" and not is_test_number) else "DEVELOPMENT"
    result["throughput_level"] = throughput
    result["is_test_number"] = is_test_number

    if is_test_number:
        result["warning"] = (
            f"You are using Meta's TEST phone number ({display_phone}). "
            "This is the default sandbox number provided by Meta — it is NOT your real business number. "
            "Messages sent from this number are ONLY delivered to phone numbers you add as 'Test Numbers' "
            "in the Meta for Developers portal. All other recipients get a 200 OK but never receive the message."
        )
        result["fix_steps"] = [
            "OPTION A (Quick test): Add your own mobile number as a 'Test Number' — "
            "Meta for Developers → Your App → WhatsApp → API Setup → 'To' field → Manage phone number list",
            "OPTION B (Production): Add and verify your real business WhatsApp number — "
            "Meta Business Suite → WhatsApp → Phone Numbers → Add Number",
        ]
    elif throughput not in ("STANDARD",):
        result["warning"] = (
            "Your account throughput is not STANDARD. Messages may only be delivered to test numbers."
        )
        result["fix_steps"] = [
            "Complete WhatsApp Business API verification in Meta Business Suite to upgrade to STANDARD throughput."
        ]
    else:
        result["warning"] = None
        result["fix_steps"] = []

    return result


@router.put("/whatsapp-config")
async def update_platform_whatsapp_config(data: WhatsAppConfig, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    config = {
        "type": "platform_whatsapp",
        "phone_number_id": data.phone_number_id,
        "access_token": data.access_token,
        "business_account_id": data.business_account_id or "",
        "webhook_verify_token": data.webhook_verify_token or "",
        "updated_at": now.isoformat(),
        "updated_by": current_user["id"]
    }
    await db.global_settings.update_one({"type": "platform_whatsapp"}, {"$set": config}, upsert=True)
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                    "update", "whatsapp_config",
                    None, {"phone_number_id": data.phone_number_id},
                    ip_address=current_user.get("_ip_address"))
    return {"message": "WhatsApp configuration updated successfully"}


# ─── WhatsApp Template Assignment Settings ────────────────────────────────────

@router.get("/whatsapp-template-settings")
async def get_whatsapp_template_settings(current_user: dict = Depends(require_admin)):
    settings = await db.global_settings.find_one({"type": "whatsapp_template_settings"}, {"_id": 0})
    if not settings:
        return {
            "invoice_template": "",
            "reminder_template": "",
            "payment_confirmation_template": "",
            "announcement_template": "",
            "payment_due_reminder_template": "",
            "operator_low_balance_template": "",
            "operator_account_expiry_template": "",
            "operator_renewal_template": "",
            "operator_daily_report_template": "",
        }
    return {
        "invoice_template": settings.get("invoice_template", ""),
        "reminder_template": settings.get("reminder_template", ""),
        "payment_confirmation_template": settings.get("payment_confirmation_template", ""),
        "announcement_template": settings.get("announcement_template", ""),
        "payment_due_reminder_template": settings.get("payment_due_reminder_template", ""),
        "operator_low_balance_template": settings.get("operator_low_balance_template", ""),
        "operator_account_expiry_template": settings.get("operator_account_expiry_template", ""),
        "operator_renewal_template": settings.get("operator_renewal_template", ""),
        "operator_daily_report_template": settings.get("operator_daily_report_template", ""),
    }


@router.put("/whatsapp-template-settings")
async def update_whatsapp_template_settings(data: WhatsAppTemplateSettings, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    settings = {
        "type": "whatsapp_template_settings",
        # Subscriber-facing templates
        "invoice_template": data.invoice_template or "",
        "reminder_template": data.reminder_template or "",
        "payment_confirmation_template": data.payment_confirmation_template or "",
        "announcement_template": data.announcement_template or "",
        "payment_due_reminder_template": data.payment_due_reminder_template or "",
        # Operator-facing templates (used by cron jobs)
        "operator_low_balance_template": data.operator_low_balance_template or "",
        "operator_account_expiry_template": data.operator_account_expiry_template or "",
        "operator_renewal_template": data.operator_renewal_template or "",
        "operator_daily_report_template": data.operator_daily_report_template or "",
        "updated_at": now.isoformat(),
        "updated_by": current_user["id"]
    }
    await db.global_settings.update_one({"type": "whatsapp_template_settings"}, {"$set": settings}, upsert=True)
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                    "update", "whatsapp_template_settings",
                    None, {"templates": {
                        "invoice": data.invoice_template,
                        "reminder": data.reminder_template,
                        "payment_confirmation": data.payment_confirmation_template,
                        "announcement": data.announcement_template,
                        "payment_due_reminder": data.payment_due_reminder_template,
                        "operator_low_balance": data.operator_low_balance_template,
                        "operator_account_expiry": data.operator_account_expiry_template,
                        "operator_renewal": data.operator_renewal_template,
                        "operator_daily_report": data.operator_daily_report_template,
                    }},
                    ip_address=current_user.get("_ip_address"))
    return {"message": "Template settings updated successfully"}


# ─── WhatsApp Test Message ────────────────────────────────────────────────────

@router.post("/whatsapp-test")
async def send_whatsapp_test_message(data: WhatsAppTestMessage, current_user: dict = Depends(require_admin)):
    """Send a test WhatsApp message using the pre-approved 'hello_world' template."""
    wa_config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
    if not wa_config or not wa_config.get("access_token"):
        raise HTTPException(status_code=400, detail="WhatsApp is not configured. Please save your WhatsApp config first.")

    if not data.phone_number or not data.phone_number.strip():
        raise HTTPException(status_code=400, detail="Phone number is required.")

    from services.whatsapp_service import WhatsAppService
    try:
        wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
        result = await wa_service.send_template_message(
            recipient_phone=data.phone_number.strip(),
            template_name="hello_world",
            language_code="en_US",
        )
        message_id = None
        if result and "messages" in result and len(result["messages"]) > 0:
            message_id = result["messages"][0].get("id")
        return {"success": True, "message": "Test message sent successfully!", "message_id": message_id}
    except Exception as e:
        error_str = str(e)
        # Log to error_logs
        from error_logger import log_error
        await log_error(
            error_type="whatsapp_error",
            message=f"WhatsApp test message failed: {error_str}",
            module="admin_whatsapp",
            endpoint="/admin/whatsapp-test",
            user_id=current_user["id"],
            user_name=current_user.get("name", ""),
            user_role="admin",
            request_method="POST",
            request_path="/api/admin/whatsapp-test",
            status_code=400,
            extra_data={"phone_number": data.phone_number},
        )
        if "not in allowed list" in error_str:
            raise HTTPException(status_code=400, detail="Recipient phone number not in allowed list. In test mode, add the number to your WhatsApp Business allowed recipients first.")
        elif "does not exist" in error_str and "template" in error_str.lower():
            raise HTTPException(status_code=400, detail="The hello_world template is not available on your WhatsApp Business account. Please check your template configuration in Meta Business Suite.")
        raise HTTPException(status_code=500, detail=f"Failed to send test message: {error_str}")


# ─── WhatsApp Template Test ───────────────────────────────────────────────────

@router.post("/whatsapp-test-template")
async def test_whatsapp_template(data: WhatsAppTemplateTestRequest, current_user: dict = Depends(require_admin)):
    """Send a test message using a specific configured template to a test number."""
    wa_config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
    if not wa_config or not wa_config.get("access_token"):
        raise HTTPException(status_code=400, detail="WhatsApp is not configured. Please save your WhatsApp config first.")

    template = await db.whatsapp_templates.find_one({"id": data.template_id, "deleted_at": None}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")

    from services.whatsapp_service import WhatsAppService

    # Build body variables — use user-supplied values first, then sensible defaults for any gaps
    body_var_names = template.get("body_variables") or []
    _defaults = {
        "customer_name": "Test Customer",
        "invoice_number": "INV-TEST-001",
        "amount": "₹999.00",
        "due_date": "31 Jul 2025",
        "plan_name": "Test Plan",
        "tenure": "Monthly",
        "days_overdue": "3",
        "payment_link": "https://example.com/pay",
        "business_name": "Test Business",
        "invoice_public_url": "https://example.com/invoice/INV-TEST-001",
        "start_date": "01 Jul 2025",
        "end_date": "31 Jul 2025",
    }
    variables: list = list(data.test_variables or [])
    for i in range(len(variables), len(body_var_names)):
        var_name = body_var_names[i]
        variables.append(_defaults.get(var_name, f"Test {var_name}"))

    # Build header params
    header_type = template.get("header_type", "none")
    header_params = None
    if header_type == "image":
        img_url = data.header_image_url or template.get("header_image_url") or ""
        header_params = [img_url] if img_url else None

    # Build button params (must match the structure expected by send_template_message)
    button_params = None
    if template.get("has_payment_button"):
        test_url = data.button_url or "https://example.com/pay/test-invoice"
        button_params = [{"sub_type": "url", "parameters": [{"type": "text", "text": test_url}]}]

    wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
    try:
        result = await wa_service.send_template_message(
            recipient_phone=data.phone_number,
            template_name=template["template_name"],
            language_code=template.get("language_code", "en"),
            variables=variables if variables else None,
            header_params=header_params,
            header_type=header_type,
            button_params=button_params,
        )
        message_id = None
        if result and result.get("messages"):
            message_id = result["messages"][0].get("id")
        return {
            "success": True,
            "message": f"Test message sent to {data.phone_number} using template '{template['display_name']}'",
            "message_id": message_id,
            "template_name": template["template_name"],
            "variables_used": variables,
        }
    except Exception as e:
        error_str = str(e)
        from error_logger import log_error
        await log_error(
            error_type="whatsapp_error",
            message=f"WhatsApp template test failed: {error_str}",
            module="admin_whatsapp",
            endpoint="/admin/whatsapp-test-template",
            user_id=current_user["id"],
            user_name=current_user.get("name", ""),
            user_role="admin",
            request_method="POST",
            request_path="/api/admin/whatsapp-test-template",
            status_code=400,
            extra_data={"phone_number": data.phone_number, "template_id": data.template_id},
        )
        if "not in allowed list" in error_str:
            raise HTTPException(status_code=400, detail="Phone not in WhatsApp allowed list (test mode). Add the number in Meta Business Manager first.")
        if "does not exist" in error_str and "template" in error_str.lower():
            raise HTTPException(status_code=400, detail=f"Template '{template['template_name']}' not found in Meta Business. Verify the template name and language code are correct.")
        raise HTTPException(status_code=500, detail=f"Template test failed: {error_str}")


# ─── Payment Gateways ────────────────────────────────────────────────────────

@router.post("/payment-gateways")
async def create_admin_payment_gateway(
    data: AdminPaymentGatewayConfig, current_user: dict = Depends(require_admin)
):
    now = datetime.now(timezone.utc)
    operator_id = data.for_operator_id or None
    if operator_id:
        operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0, "id": 1})
        if not operator:
            raise HTTPException(status_code=404, detail="Operator not found")
    gateway = {
        "id": generate_id(), "gateway_type": data.gateway_type,
        "api_key": data.api_key, "api_secret": data.api_secret,
        "webhook_secret": data.webhook_secret, "is_active": data.is_active,
        "operator_id": operator_id,
        "is_platform_gateway": operator_id is None,
        "created_by": current_user["id"],
        "created_at": now.isoformat(), "updated_at": now.isoformat()
    }
    query = {"operator_id": operator_id} if operator_id else {"operator_id": None, "gateway_type": data.gateway_type}
    await db.payment_gateways.update_one(
        query,
        {"$set": gateway}, upsert=True
    )
    return {"message": "Payment gateway configured successfully", "id": gateway["id"]}


@router.get("/payment-gateways")
async def get_admin_payment_gateways(current_user: dict = Depends(require_admin)):
    gateways = await db.payment_gateways.find({}, {"_id": 0, "api_secret": 0}).to_list(100)
    operator_ids = [g["operator_id"] for g in gateways if g.get("operator_id")]
    operator_map = {}
    if operator_ids:
        operators = await db.operators.find(
            {"id": {"$in": operator_ids}, "deleted_at": None},
            {"_id": 0, "id": 1, "company_name": 1}
        ).to_list(200)
        operator_map = {op["id"]: op.get("company_name", op["id"]) for op in operators}
    for g in gateways:
        if g.get("api_key"):
            g["api_key"] = g["api_key"][:8] + "****"
        if g.get("operator_id"):
            g["operator_name"] = operator_map.get(g["operator_id"], g["operator_id"])
    return gateways


@router.delete("/payment-gateways/{gateway_id}")
async def delete_admin_payment_gateway(gateway_id: str, current_user: dict = Depends(require_admin)):
    result = await db.payment_gateways.delete_one({"id": gateway_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Gateway not found")
    return {"message": "Gateway deleted"}


# ─── Dashboard ───────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_admin_dashboard(current_user: dict = Depends(require_admin)):
    total_operators = await db.operators.count_documents({"deleted_at": None})
    active_operators = await db.operators.count_documents({"status": "active", "deleted_at": None})
    trial_operators = await db.operators.count_documents({"status": "trial", "deleted_at": None})
    suspended_operators = await db.operators.count_documents({"status": "suspended", "deleted_at": None})
    read_only_operators = await db.operators.count_documents({"is_read_only": True, "deleted_at": None})

    # ── Subscriber-level stats across all operators ──
    total_subscribers = await db.subscribers.count_documents({"deleted_at": None})
    active_subscribers = await db.subscribers.count_documents({"status": "active", "deleted_at": None})
    suspended_subscribers = await db.subscribers.count_documents({"status": "suspended", "deleted_at": None})

    # ── Approx monthly invoice-charge revenue across the platform ──
    # = Σ (operator's per_invoice_price × operator's active subscriber count)
    saas_plan_charge_map: dict[str, float] = {}
    async for p in db.saas_plans.find({"deleted_at": None}, {"_id": 0, "id": 1, "per_invoice_price": 1}):
        saas_plan_charge_map[p["id"]] = float(p.get("per_invoice_price") or 10.0)
    approx_monthly_revenue = 0.0
    async for op in db.operators.find(
        {"status": "active", "deleted_at": None}, {"_id": 0, "id": 1, "saas_plan_id": 1}
    ):
        charge = saas_plan_charge_map.get(op.get("saas_plan_id") or "", 10.0)
        op_active_subs = await db.subscribers.count_documents(
            {"operator_id": op["id"], "status": "active", "deleted_at": None}
        )
        approx_monthly_revenue += charge * op_active_subs

    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    expiring_date = (now + timedelta(days=7)).isoformat()
    expiring_operators = await db.operators.count_documents({
        "subscription_ends_at": {"$lte": expiring_date, "$gte": now.isoformat()}, "deleted_at": None
    })

    all_payments = await db.saas_payments.find({"status": "completed", "deleted_at": None}, {"_id": 0}).to_list(10000)
    month_payments = [p for p in all_payments if p.get("created_at", "") >= start_of_month.isoformat()]

    saas_revenue_this_month = sum(p.get("base_amount", 0) for p in month_payments if p.get("item_type") == "subscription")
    addon_revenue_this_month = sum(p.get("base_amount", 0) for p in month_payments if p.get("item_type") == "addon")
    gst_collected_this_month = sum(p.get("gst_amount", 0) for p in month_payments)
    total_saas_revenue = sum(p.get("base_amount", 0) for p in all_payments if p.get("item_type") == "subscription")
    total_addon_revenue = sum(p.get("base_amount", 0) for p in all_payments if p.get("item_type") == "addon")
    total_gst_collected = sum(p.get("gst_amount", 0) for p in all_payments)

    recent_raw = sorted(all_payments, key=lambda x: x.get("created_at", ""), reverse=True)[:10]
    op_ids = list({p["operator_id"] for p in recent_raw})
    ops = await db.operators.find({"id": {"$in": op_ids}}, {"_id": 0, "id": 1, "company_name": 1}).to_list(100)
    op_map = {o["id"]: o.get("company_name", "Unknown") for o in ops}
    recent_payments = [
        {
            "id": p.get("id"), "operator_name": op_map.get(p.get("operator_id", ""), "Unknown"),
            "item_type": p.get("item_type"), "item_code": p.get("item_code", ""),
            "base_amount": p.get("base_amount", 0), "gst_amount": p.get("gst_amount", 0),
            "total_amount": p.get("total_amount", 0), "created_at": p.get("created_at"),
        }
        for p in recent_raw
    ]

    return {
        "total_operators": total_operators, "active_operators": active_operators,
        "trial_operators": trial_operators, "suspended_operators": suspended_operators,
        "read_only_operators": read_only_operators, "expiring_operators": expiring_operators,
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "suspended_subscribers": suspended_subscribers,
        "approx_monthly_revenue": round(approx_monthly_revenue, 2),
        "saas_revenue_this_month": round(saas_revenue_this_month, 2),
        "addon_revenue_this_month": round(addon_revenue_this_month, 2),
        "gst_collected_this_month": round(gst_collected_this_month, 2),
        "total_saas_revenue": round(total_saas_revenue, 2),
        "total_addon_revenue": round(total_addon_revenue, 2),
        "total_gst_collected": round(total_gst_collected, 2),
        "recent_payments": recent_payments,
    }


# ─── Audit Logs ──────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_all_audit_logs(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    action: Optional[str] = None,
    role: Optional[str] = None,
    module: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    query: dict = {}
    # Text search across user_name, module, ip_address
    if search:
        query["$or"] = [
            {"user_name": {"$regex": search, "$options": "i"}},
            {"module":    {"$regex": search, "$options": "i"}},
            {"ip_address":{"$regex": search, "$options": "i"}},
        ]
    if action:
        query["action"] = action
    if role:
        query["role"] = role
    if module and not search:
        query["module"] = {"$regex": module, "$options": "i"}
    if date_from or date_to:
        date_q: dict = {}
        if date_from:
            date_q["$gte"] = date_from
        if date_to:
            # include the full end day
            date_q["$lt"] = date_to + "T23:59:59"
        query["created_at"] = date_q

    total = await db.audit_logs.count_documents(query)
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    result = []
    for log in logs:
        try:
            if isinstance(log.get("old_value"), str):
                log["old_value"] = {"value": log["old_value"]}
            if isinstance(log.get("new_value"), str):
                log["new_value"] = {"value": log["new_value"]}
            log["created_at"] = datetime.fromisoformat(log["created_at"])
            serialized = AuditLogResponse(**log).model_dump()
            serialized["created_at"] = serialized["created_at"].isoformat()
            result.append(serialized)
        except Exception:
            continue
    return {"logs": result, "total": total}


# ─── Reports ─────────────────────────────────────────────────────────────────

@router.get("/reports/payments")
async def get_admin_payment_reports(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    query = {"status": "paid", "deleted_at": None}
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        query.setdefault("created_at", {})["$lte"] = end_date

    invoices = await db.invoices.find(query, {"_id": 0}).to_list(10000)
    operator_revenue = {}
    total_revenue = total_tax = 0

    for inv in invoices:
        op_id = inv.get("operator_id")
        if op_id not in operator_revenue:
            operator_revenue[op_id] = {"count": 0, "revenue": 0, "tax": 0}
        operator_revenue[op_id]["count"] += 1
        operator_revenue[op_id]["revenue"] += inv.get("final_amount", 0)
        operator_revenue[op_id]["tax"] += inv.get("tax_amount", 0)
        total_revenue += inv.get("final_amount", 0)
        total_tax += inv.get("tax_amount", 0)

    for op_id in operator_revenue:
        operator = await db.operators.find_one({"id": op_id}, {"_id": 0, "company_name": 1})
        operator_revenue[op_id]["company_name"] = operator.get("company_name", "Unknown") if operator else "Unknown"

    return {
        "total_invoices": len(invoices), "total_revenue": round(total_revenue, 2),
        "total_tax": round(total_tax, 2), "by_operator": list(operator_revenue.values())
    }


@router.get("/reports/saas-revenue")
async def get_saas_revenue_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    query = {"deleted_at": None}
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        query.setdefault("created_at", {})["$lte"] = end_date + "T23:59:59"

    payments = await db.saas_payments.find(query, {"_id": 0}).to_list(10000)
    total = sum(p.get("total_amount", 0) for p in payments)
    gst = sum(p.get("gst_amount", 0) for p in payments)

    return {
        "total_payments": len(payments), "total_revenue": round(total, 2),
        "total_gst": round(gst, 2),
    }


@router.get("/reports/saas-subscriptions")
async def get_saas_subscriptions(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Paginated list of SaaS subscription payments with operator info — for Admin Reports."""
    query: dict = {"deleted_at": None, "status": "completed"}
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        query.setdefault("created_at", {})["$lte"] = end_date + "T23:59:59"

    payments = await db.saas_payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)

    # Enrich with operator company_name
    op_cache: dict = {}
    for p in payments:
        oid = p.get("operator_id", "")
        if oid not in op_cache:
            op = await db.operators.find_one({"id": oid}, {"_id": 0, "company_name": 1, "owner_name": 1, "email": 1})
            op_cache[oid] = op or {}
        p["company_name"] = op_cache[oid].get("company_name", "—")
        p["owner_name"] = op_cache[oid].get("owner_name", "—")
        p["email"] = op_cache[oid].get("email", "—")

        # Resolve plan name from item_code
        plan_name = p.get("item_code", "")
        if p.get("item_type") == "subscription" and plan_name:
            plan_doc = await db.saas_plans.find_one({"id": plan_name}, {"_id": 0, "name": 1})
            p["plan_name"] = plan_doc["name"] if plan_doc else plan_name
        else:
            p["plan_name"] = p.get("item_type", "—").replace("_", " ").title()

    # Search filter (company_name, owner_name, plan_name, email)
    if search:
        s = search.lower()
        payments = [
            p for p in payments
            if s in p.get("company_name", "").lower()
            or s in p.get("owner_name", "").lower()
            or s in p.get("plan_name", "").lower()
            or s in p.get("email", "").lower()
        ]

    total_count = len(payments)
    start = (page - 1) * limit
    page_items = payments[start: start + limit]

    result = []
    for p in page_items:
        result.append({
            "id": p.get("id", ""),
            "created_at": p.get("created_at", ""),
            "company_name": p.get("company_name", "—"),
            "owner_name": p.get("owner_name", "—"),
            "email": p.get("email", "—"),
            "item_type": p.get("item_type", "—"),
            "plan_name": p.get("plan_name", "—"),
            "months": p.get("months", 1) if isinstance(p.get("months"), int) else 1,
            "base_amount": p.get("base_amount", 0),
            "discount_amount": p.get("discount_amount", 0),
            "coupon_code": p.get("coupon_code"),
            "gst_amount": p.get("gst_amount", 0),
            "total_amount": p.get("total_amount", 0),
            "status": p.get("status", "—"),
        })

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": max(1, (total_count + limit - 1) // limit),
        "subscriptions": result,
    }


# ─── Cron Triggers ───────────────────────────────────────────────────────────

@router.post("/cron/generate-invoices")
async def trigger_invoice_generation(current_user: dict = Depends(require_admin)):
    from services.cron_service import CronJobService
    platform_settings = await db.global_settings.find_one({"type": "platform"}, {"_id": 0}) or {}
    days_before = int(platform_settings.get("auto_invoice_days_before", 3) or 3)
    service = CronJobService(db)
    results = await service.generate_upcoming_invoices(days_before=days_before)
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "trigger", "cron_jobs", None, {"action": "generate_invoices", "results": results},
        ip_address=current_user.get("_ip_address")
    )
    return results


@router.post("/cron/send-reminders")
async def trigger_reminders(current_user: dict = Depends(require_admin)):
    from services.cron_service import CronJobService
    service = CronJobService(db)
    return await service.send_overdue_reminders(days_overdue=1)


@router.post("/cron/process-scheduled-reminders")
async def trigger_scheduled_reminders(current_user: dict = Depends(require_admin)):
    """Manually trigger processing of operator-configured scheduled reminders."""
    from services.cron_service import CronJobService
    service = CronJobService(db)
    results = await service.process_scheduled_reminders()
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "trigger", "cron_jobs", None, {"action": "process_scheduled_reminders", "results": results},
        ip_address=current_user.get("_ip_address")
    )
    return results


@router.post("/cron/check-expiry")
async def trigger_expiry_check(current_user: dict = Depends(require_admin)):
    from services.cron_service import run_daily_expiry_check
    results = await run_daily_expiry_check(db)
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "trigger", "cron_jobs", None, {"action": "check_expiry", "results": results},
        ip_address=current_user.get("_ip_address")
    )
    return results


@router.post("/cron/check-wallet")
async def trigger_wallet_check(current_user: dict = Depends(require_admin)):
    """Manually trigger the daily wallet balance check & operator WA alerts."""
    from services.cron_service import run_daily_wallet_check
    results = await run_daily_wallet_check(db)
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "trigger", "cron_jobs", None, {"action": "check_wallet", "results": results},
        ip_address=current_user.get("_ip_address")
    )
    return results


@router.post("/cron/send-operator-report")
async def trigger_operator_report(current_user: dict = Depends(require_admin)):
    """Manually trigger the daily operator WA report. Returns per-operator results."""
    from services.cron_service import run_daily_operator_report
    results = await run_daily_operator_report(db)
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "trigger", "cron_jobs", None, {"action": "send_operator_report", "results": results},
        ip_address=current_user.get("_ip_address")
    )
    return results


@router.get("/cron/status")
async def get_cron_status(request: Request, current_user: dict = Depends(require_admin)):
    """Return next run times for all scheduled cron jobs (in IST)."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if not scheduler:
        return {"error": "Scheduler not available"}
    jobs = scheduler.get_jobs()
    import pytz
    ist = pytz.timezone("Asia/Kolkata")
    return {
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_utc": job.next_run_time.isoformat() if job.next_run_time else None,
                "next_run_ist": job.next_run_time.astimezone(ist).strftime("%Y-%m-%d %H:%M:%S IST") if job.next_run_time else None,
            }
            for job in jobs
        ]
    }



# ─── Discount Codes ──────────────────────────────────────────────────────────

@router.get("/discount-codes", response_model=List[DiscountCodeResponse])
async def list_discount_codes(current_user: dict = Depends(require_admin)):
    codes = await db.discount_codes.find({"deleted_at": None}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [
        DiscountCodeResponse(**{**c, "created_at": datetime.fromisoformat(c["created_at"])})
        for c in codes
    ]


@router.post("/discount-codes", response_model=DiscountCodeResponse)
async def create_discount_code(data: DiscountCodeCreate, current_user: dict = Depends(require_admin)):
    existing = await db.discount_codes.find_one({"code": data.code.upper(), "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Discount code already exists")
    now = datetime.now(timezone.utc)
    doc = {
        "id": generate_id(),
        "code": data.code.upper(),
        "description": data.description,
        "discount_type": data.discount_type,
        "discount_value": data.discount_value,
        "expiry_date": data.expiry_date,
        "max_redemptions": data.max_redemptions,
        "used_count": 0,
        "is_active": data.is_active,
        "created_by": current_user.get("id", ""),
        "created_at": now.isoformat(),
        "deleted_at": None,
    }
    await db.discount_codes.insert_one(doc)
    doc.pop("_id", None)
    return DiscountCodeResponse(**{**doc, "created_at": now})


@router.patch("/discount-codes/{code_id}/toggle")
async def toggle_discount_code(code_id: str, current_user: dict = Depends(require_admin)):
    doc = await db.discount_codes.find_one({"id": code_id, "deleted_at": None}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Discount code not found")
    new_state = not doc.get("is_active", True)
    await db.discount_codes.update_one({"id": code_id}, {"$set": {"is_active": new_state}})
    return {"message": f"Discount code {'activated' if new_state else 'deactivated'}", "is_active": new_state}


@router.delete("/discount-codes/{code_id}")
async def delete_discount_code(code_id: str, current_user: dict = Depends(require_admin)):
    result = await db.discount_codes.update_one(
        {"id": code_id, "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Discount code not found")
    return {"message": "Discount code deleted"}


# ─── WhatsApp Templates Management ─────────────────────────────────────────

@router.post("/whatsapp-templates")
async def create_whatsapp_template(data: WhatsAppTemplateCreate, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    # Check for duplicate template_name
    existing = await db.whatsapp_templates.find_one({"template_name": data.template_name, "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="A template with this name already exists")
    template = {
        "id": generate_id(),
        "template_name": data.template_name,
        "display_name": data.display_name,
        "template_type": data.template_type,
        "language_code": data.language_code,
        "description": data.description or "",
        "body_variables": data.body_variables or [],
        "header_type": data.header_type or "none",
        "header_image_url": data.header_image_url or "",
        "header_variable": data.header_variable,
        "header_image_static": data.header_image_static,
        "has_payment_button": data.has_payment_button,
        "button_url_variable": data.button_url_variable or "invoice_public_url",
        "is_active": data.is_active,
        "created_by": current_user["id"],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.whatsapp_templates.insert_one(template)
    template.pop("_id", None)
    return template


@router.get("/whatsapp-templates")
async def list_whatsapp_templates(
    template_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(require_admin)
):
    query = {"deleted_at": None}
    if template_type:
        query["template_type"] = template_type
    if is_active is not None:
        query["is_active"] = is_active
    templates = await db.whatsapp_templates.find(query, {"_id": 0}).to_list(200)
    return templates


@router.get("/whatsapp-templates/{template_id}")
async def get_whatsapp_template(template_id: str, current_user: dict = Depends(require_admin)):
    template = await db.whatsapp_templates.find_one({"id": template_id, "deleted_at": None}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/whatsapp-templates/{template_id}")
async def update_whatsapp_template(
    template_id: str, data: WhatsAppTemplateUpdate, current_user: dict = Depends(require_admin)
):
    template = await db.whatsapp_templates.find_one({"id": template_id, "deleted_at": None}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    # Exclude None values BUT allow False (bool) and empty list (body_variables can be cleared)
    raw = data.model_dump()
    update_data = {}
    for k, v in raw.items():
        if v is None:
            continue  # skip truly unset fields
        update_data[k] = v
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    # Check for duplicate template_name if changing it
    if "template_name" in update_data and update_data["template_name"] != template["template_name"]:
        existing = await db.whatsapp_templates.find_one(
            {"template_name": update_data["template_name"], "deleted_at": None, "id": {"$ne": template_id}}
        )
        if existing:
            raise HTTPException(status_code=400, detail="A template with this name already exists")
    await db.whatsapp_templates.update_one({"id": template_id}, {"$set": update_data})
    updated = await db.whatsapp_templates.find_one({"id": template_id}, {"_id": 0})
    return updated


@router.delete("/whatsapp-templates/{template_id}")
async def delete_whatsapp_template(template_id: str, current_user: dict = Depends(require_admin)):
    result = await db.whatsapp_templates.update_one(
        {"id": template_id, "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully"}


@router.patch("/whatsapp-templates/{template_id}/toggle")
async def toggle_whatsapp_template(template_id: str, current_user: dict = Depends(require_admin)):
    template = await db.whatsapp_templates.find_one({"id": template_id, "deleted_at": None}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    new_state = not template.get("is_active", True)
    await db.whatsapp_templates.update_one({"id": template_id}, {"$set": {"is_active": new_state}})
    return {"message": f"Template {'activated' if new_state else 'deactivated'}", "is_active": new_state}


# ─── WhatsApp Stats & Message Logs ────────────────────────────────────────────

@router.get("/whatsapp-stats")
async def get_whatsapp_stats(current_user: dict = Depends(require_admin)):
    """Get aggregated WhatsApp message sending statistics."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%dT00:00:00")
    month_str = now.strftime("%Y-%m-01T00:00:00")

    total = await db.whatsapp_message_logs.count_documents({})
    total_today = await db.whatsapp_message_logs.count_documents({"created_at": {"$gte": today_str}})
    total_month = await db.whatsapp_message_logs.count_documents({"created_at": {"$gte": month_str}})
    total_sent = await db.whatsapp_message_logs.count_documents({"status": "sent"})
    total_failed = await db.whatsapp_message_logs.count_documents({"status": "failed"})

    # By template name
    templates_pipeline = [
        {"$group": {"_id": "$template_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    templates_agg = await db.whatsapp_message_logs.aggregate(templates_pipeline).to_list(10)
    by_template = {t["_id"]: t["count"] for t in templates_agg if t["_id"]}

    # By category
    categories_pipeline = [
        {"$group": {"_id": "$template_category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    categories_agg = await db.whatsapp_message_logs.aggregate(categories_pipeline).to_list(20)
    by_category = {c["_id"]: c["count"] for c in categories_agg if c["_id"]}

    # By trigger
    trigger_pipeline = [
        {"$group": {"_id": "$trigger", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    trigger_agg = await db.whatsapp_message_logs.aggregate(trigger_pipeline).to_list(10)
    by_trigger = {t["_id"]: t["count"] for t in trigger_agg if t["_id"]}

    # Last 7 days daily breakdown
    seven_days_ago = (now - timedelta(days=6)).strftime("%Y-%m-%dT00:00:00")
    recent_pipeline = [
        {"$match": {"created_at": {"$gte": seven_days_ago}}},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "sent": {"$sum": {"$cond": [{"$eq": ["$status", "sent"]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}}
        }},
        {"$sort": {"_id": 1}}
    ]
    recent_agg = await db.whatsapp_message_logs.aggregate(recent_pipeline).to_list(7)
    recent_7_days = [{"date": r["_id"], "sent": r["sent"], "failed": r["failed"]} for r in recent_agg]

    return {
        "total": total,
        "today": total_today,
        "this_month": total_month,
        "sent": total_sent,
        "failed": total_failed,
        "success_rate": round(total_sent / total * 100, 1) if total > 0 else 0,
        "by_template": by_template,
        "by_category": by_category,
        "by_trigger": by_trigger,
        "recent_7_days": recent_7_days,
    }


@router.get("/whatsapp-message-logs")
async def get_whatsapp_message_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=20),
    status: Optional[str] = None,
    delivery_status: Optional[str] = None,
    template: Optional[str] = None,
    template_category: Optional[str] = None,
    operator_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Get paginated WhatsApp message logs with filters."""
    query = {}
    if status:
        query["status"] = status
    if delivery_status:
        # delivery_status mirrors WhatsApp webhook statuses: sent | delivered | read | failed
        query["delivery_status"] = delivery_status
    if template:
        query["template_name"] = {"$regex": template, "$options": "i"}
    if template_category:
        query["template_category"] = template_category
    if operator_id:
        query["operator_id"] = operator_id
    if search:
        query["$or"] = [
            {"recipient_phone": {"$regex": search, "$options": "i"}},
            {"template_name": {"$regex": search, "$options": "i"}},
            {"invoice_number": {"$regex": search, "$options": "i"}},
            {"wa_id": {"$regex": search, "$options": "i"}},
        ]
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to + "T23:59:59"
        query["created_at"] = date_filter

    total = await db.whatsapp_message_logs.count_documents(query)
    skip = (page - 1) * per_page
    logs = await db.whatsapp_message_logs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(per_page).to_list(per_page)

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


@router.delete("/whatsapp-message-logs")
async def clear_whatsapp_message_logs(current_user: dict = Depends(require_admin)):
    """Clear all WhatsApp message logs."""
    result = await db.whatsapp_message_logs.delete_many({})
    return {"message": f"Cleared {result.deleted_count} WhatsApp message logs"}


# ─── Error Logs ───────────────────────────────────────────────────────────────

@router.get("/error-logs")
async def get_error_logs(
    page: int = 1,
    per_page: int = 50,
    error_type: str = None,
    module: str = None,
    status_code: int = None,
    search: str = None,
    date_from: str = None,
    date_to: str = None,
    current_user: dict = Depends(require_admin)
):
    """Get paginated error logs with filters."""
    query = {}

    if error_type:
        query["error_type"] = error_type
    if module:
        query["module"] = {"$regex": module, "$options": "i"}
    if status_code:
        query["status_code"] = status_code
    if search:
        query["$or"] = [
            {"message": {"$regex": search, "$options": "i"}},
            {"endpoint": {"$regex": search, "$options": "i"}},
            {"user_name": {"$regex": search, "$options": "i"}},
            {"request_path": {"$regex": search, "$options": "i"}},
        ]
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to + "T23:59:59"
        query["created_at"] = date_filter

    total = await db.error_logs.count_documents(query)
    skip = (page - 1) * per_page

    logs = await db.error_logs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(per_page).to_list(per_page)

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


@router.get("/error-logs/stats")
async def get_error_logs_stats(current_user: dict = Depends(require_admin)):
    """Get error log statistics."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%dT00:00:00")

    total_all = await db.error_logs.count_documents({})
    total_today = await db.error_logs.count_documents({"created_at": {"$gte": today_str}})
    total_server = await db.error_logs.count_documents({"error_type": "server_error"})
    total_client = await db.error_logs.count_documents({"error_type": "client_error"})
    total_validation = await db.error_logs.count_documents({"error_type": "validation_error"})
    total_unhandled = await db.error_logs.count_documents({"error_type": "unhandled_exception"})

    return {
        "total": total_all,
        "today": total_today,
        "by_type": {
            "server_error": total_server,
            "client_error": total_client,
            "validation_error": total_validation,
            "unhandled_exception": total_unhandled,
        }
    }


@router.delete("/error-logs")
async def clear_error_logs(current_user: dict = Depends(require_admin)):
    """Clear all error logs."""
    result = await db.error_logs.delete_many({})
    return {"message": f"Cleared {result.deleted_count} error logs"}


# ─── System Reset (Danger Zone) ───────────────────────────────────────────────

def _generate_reset_otp() -> str:
    import secrets
    return str(secrets.randbelow(900000) + 100000)


@router.post("/reset/request-otp")
async def request_system_reset_otp(current_user: dict = Depends(require_admin)):
    """Send a 6-digit OTP to admin email to authorize full data reset."""
    from services.email_service import get_email_service_async
    otp = _generate_reset_otp()
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(minutes=10)).isoformat()
    await db.global_settings.update_one(
        {"type": "admin_reset_otp"},
        {"$set": {
            "type": "admin_reset_otp",
            "otp": otp,
            "admin_id": current_user["id"],
            "created_at": now.isoformat(),
            "expires_at": expires_at,
            "used": False,
        }},
        upsert=True
    )
    try:
        email_service = await get_email_service_async()
        await email_service.send_email(
            to_email=current_user["email"],
            subject="E-Bill Admin System Reset OTP",
            html=(
                "<p>A <strong>full system data reset</strong> has been requested for your E-Bill admin account.</p>"
                f"<p>Your reset OTP is: <strong style='font-size:1.5em;letter-spacing:4px'>{otp}</strong></p>"
                "<p>This code is valid for <strong>10 minutes</strong>.</p>"
                "<p style='color:red;'><strong>WARNING:</strong> This will permanently delete all operator, subscriber, "
                "invoice, wallet, and log data. Admin settings will NOT be affected.</p>"
                "<p>If you did not request this reset, please ignore this email.</p>"
            ),
            text=(
                f"Your E-Bill admin system reset OTP is: {otp}\n"
                "Valid for 10 minutes.\n"
                "WARNING: This will permanently delete all operator and related data.\n"
                "Do NOT share this code."
            ),
        )
    except Exception as e:
        await db.global_settings.delete_one({"type": "admin_reset_otp"})
        raise HTTPException(status_code=500, detail=f"Failed to send OTP email: {str(e)}")
    return {"message": f"Reset OTP sent to {current_user['email']}. Valid for 10 minutes."}


@router.post("/reset/execute")
async def execute_system_reset(data: SystemResetOTPRequest, current_user: dict = Depends(require_admin)):
    """Execute full data reset after OTP verification. Admin settings and accounts are preserved."""
    now = datetime.now(timezone.utc)
    otp_doc = await db.global_settings.find_one({"type": "admin_reset_otp"}, {"_id": 0})
    if not otp_doc:
        raise HTTPException(status_code=400, detail="No pending reset OTP. Request one first.")
    if otp_doc.get("used"):
        raise HTTPException(status_code=400, detail="OTP already used. Request a new one.")
    if otp_doc.get("admin_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="OTP belongs to a different admin session.")
    if now.isoformat() > otp_doc.get("expires_at", ""):
        raise HTTPException(status_code=400, detail="OTP has expired. Request a new one.")
    if otp_doc.get("otp") != data.otp.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    await db.global_settings.update_one({"type": "admin_reset_otp"}, {"$set": {"used": True}})

    deleted_at = now.isoformat()
    reset_summary = {}

    # Soft-delete operator-owned records
    for col, filt, key in [
        ("operators", {}, "operators"),
        ("users", {"role": {"$in": ["operator", "staff"]}}, "users"),
        ("subscribers", {}, "subscribers"),
        ("operator_plans", {}, "plans"),
        ("invoices", {}, "invoices"),
    ]:
        r = await db[col].update_many(filt, {"$set": {"deleted_at": deleted_at}})
        reset_summary[key] = r.modified_count

    # Hard-delete config, wallet, log data
    # Note: WhatsApp logs/templates, backup files, and payment gateway settings are preserved (admin-level settings)
    for col, key in [
        ("operator_wallets", "wallets"),
        ("wallet_transactions", "wallet_transactions"),
        ("invoice_settings", "invoice_settings"),
        ("operator_theme", "themes"),
        ("notification_queue", "notifications"),
        ("checkout_orders", "checkout_orders"),
        ("announcements", "announcements"),
        ("saas_payments", "saas_payments"),
        ("audit_logs", "audit_logs"),
        ("error_logs", "error_logs"),
        ("support_tickets", "support_tickets"),
    ]:
        res = await db[col].delete_many({})
        reset_summary[key] = res.deleted_count

    # Only delete operator-specific payment gateway configs, preserve platform-level gateways
    pg_result = await db.payment_gateways.delete_many({"operator_id": {"$exists": True, "$ne": None}})
    reset_summary["payment_gateways"] = pg_result.deleted_count

    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "delete", "system_reset",
        None,
        {"reset_summary": reset_summary},
        ip_address=current_user.get("_ip_address")
    )
    return {
        "message": "System reset complete. All operator data removed. Admin settings preserved.",
        "summary": reset_summary,
    }


# ─── Landing Page Settings ────────────────────────────────────────────────────

DEFAULT_LANDING_PAGE_SETTINGS = {
    "brand": {
        "name": "E-Bill",
        "tagline": "ISP & Cable Billing Solutions",
        "business_name": "Teasy Services",
        "logo_url": "/ebill-logo.svg",
    },
    "colors": {
        "primary": "#0066B2",
        "secondary": "#44AB62",
        "background": "#EFEFEF",
        "accent": "#004080",
    },
    "hero": {
        "badge": "India's GST-Ready Billing Platform",
        "title": "Automate Your",
        "title_highlight": "Recurring Billing",
        "subtitle": "Multi-tenant billing platform for subscription businesses in India. Auto-generate invoices, send WhatsApp reminders, and collect payments through your own payment gateway.",
        "cta_primary": "Start Free Trial",
        "cta_secondary": "Watch Demo",
        "features": ["No credit card required", "GST compliant invoices", "WhatsApp integration"],
    },
    "stats": {
        "stat1_value": "10K+",
        "stat1_label": "Active Subscribers",
        "stat2_value": "₹5Cr+",
        "stat2_label": "Processed Monthly",
        "stat3_value": "500+",
        "stat3_label": "Businesses Trust Us",
        "stat4_value": "99.9%",
        "stat4_label": "Uptime",
    },
    "features": {
        "title": "Everything You Need to Manage Billing",
        "subtitle": "A complete solution for subscription businesses with GST compliance, automated workflows, and seamless payment collection.",
    },
    "contact": {
        "email": "support@teasyservices.com",
        "phone": "+91 98765 43210",
        "whatsapp": "+91 98765 43210",
    },
    "footer": {
        "copyright": "© 2026 E-Bill by Teasy Services. All rights reserved.",
        "tagline": "Made in India 🇮🇳",
    },
}


@router.get("/landing-page")
async def get_landing_page_settings(current_user: dict = Depends(require_admin)):
    """Get landing page customization settings."""
    settings = await db.global_settings.find_one({"type": "landing_page"}, {"_id": 0})
    if not settings:
        return DEFAULT_LANDING_PAGE_SETTINGS
    return settings.get("settings", DEFAULT_LANDING_PAGE_SETTINGS)


@router.put("/landing-page")
async def update_landing_page_settings(
    settings: dict,
    current_user: dict = Depends(require_admin),
):
    """Update landing page customization settings."""
    now = datetime.now(timezone.utc)
    await db.global_settings.update_one(
        {"type": "landing_page"},
        {"$set": {"type": "landing_page", "settings": settings, "updated_at": now.isoformat()}},
        upsert=True,
    )
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "update", "landing_page", None, {"updated": True},
        ip_address=current_user.get("_ip_address")
    )
    return {"message": "Landing page settings updated successfully", "settings": settings}


# Public endpoint (no auth required) for landing page to fetch settings
@router.get("/public/landing-page")
async def get_public_landing_page_settings():
    """Get landing page settings for public display (no auth required)."""
    settings = await db.global_settings.find_one({"type": "landing_page"}, {"_id": 0})
    if not settings:
        return DEFAULT_LANDING_PAGE_SETTINGS
    return settings.get("settings", DEFAULT_LANDING_PAGE_SETTINGS)



@router.post("/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """Upload a logo image for the landing page."""
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, and SVG images are allowed")
    
    # Validate file size (5MB max)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    # Generate unique filename
    safe_original = sanitize_filename(file.filename or "logo.png", default="logo")
    ext = safe_original.split(".")[-1].lower() if "." in safe_original else "png"
    filename = f"logo_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    with open(filepath, "wb") as f:
        f.write(content)
    
    # Return the public URL
    public_url = f"/uploads/{filename}"
    
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "upload", "logo", None, {"filename": filename},
        ip_address=current_user.get("_ip_address")
    )
    
    return {"message": "Logo uploaded successfully", "url": public_url, "filename": filename}


# ─── Email Settings ───────────────────────────────────────────────────────────

@router.get("/email-settings")
async def get_email_settings(current_user: dict = Depends(require_admin)):
    """Get current email API configuration (Resend with SMTP fallback)."""
    doc = await get_global_settings_doc({"key": "email_settings"}, {"_id": 0})
    if doc:
        return {
            "resend_api_key_preview": (doc.get("resend_api_key") or "")[:8] + "****" if doc.get("resend_api_key") else "",
            "resend_from_email": doc.get("resend_from_email", ""),
            "smtp_host": doc.get("smtp_host", ""),
            "smtp_port": doc.get("smtp_port", 587),
            "smtp_username": doc.get("smtp_username", ""),
            "smtp_from_email": doc.get("smtp_from_email", ""),
            "smtp_use_tls": doc.get("smtp_use_tls", True),
            "is_configured": bool(doc.get("resend_api_key")),
            "is_smtp_configured": bool(doc.get("smtp_host")),
        }
    # Fall back to env vars
    env_key = os.environ.get("RESEND_API_KEY", "")
    return {
        "resend_api_key_preview": env_key[:8] + "****" if env_key else "",
        "resend_from_email": os.environ.get("RESEND_FROM_EMAIL", ""),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "smtp_username": os.environ.get("SMTP_USERNAME", ""),
        "smtp_from_email": os.environ.get("SMTP_FROM_EMAIL", ""),
        "smtp_use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() != "false",
        "is_configured": bool(env_key),
        "is_smtp_configured": bool(os.environ.get("SMTP_HOST", "")),
    }


@router.put("/email-settings")
async def update_email_settings(
    data: EmailSettingsUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update email credentials stored in DB, including SMTP fallback settings."""
    now = datetime.now(timezone.utc)
    existing = await get_global_settings_doc({"key": "email_settings"}, {"_id": 0}) or {}
    resend_api_key = (data.resend_api_key or "").strip()
    resend_from_email = (data.resend_from_email or "").strip()
    smtp_host = (data.smtp_host or "").strip()
    smtp_from_email = (data.smtp_from_email or "").strip()

    has_resend = bool(resend_api_key or resend_from_email)
    has_smtp = bool(smtp_host)

    if not has_resend and not has_smtp:
        raise HTTPException(
            status_code=400,
            detail="Configure either Resend or SMTP to enable email delivery",
        )
    if resend_api_key and not resend_from_email:
        raise HTTPException(status_code=400, detail="Resend from email is required when using Resend")
    if smtp_host and not smtp_from_email and not resend_from_email:
        raise HTTPException(status_code=400, detail="SMTP from email is required when SMTP is configured")

    update_doc = {
        "key": "email_settings",
        "resend_from_email": resend_from_email or existing.get("resend_from_email", ""),
        "smtp_host": smtp_host,
        "smtp_port": data.smtp_port,
        "smtp_username": data.smtp_username or "",
        "smtp_from_email": smtp_from_email or existing.get("smtp_from_email", ""),
        "smtp_use_tls": data.smtp_use_tls,
        "updated_at": now.isoformat(),
    }
    if resend_api_key:
        update_doc["resend_api_key"] = resend_api_key
    elif existing.get("resend_api_key"):
        update_doc["resend_api_key"] = existing["resend_api_key"]
    if data.smtp_password:
        update_doc["smtp_password"] = data.smtp_password
    elif existing.get("smtp_password"):
        update_doc["smtp_password"] = existing["smtp_password"]

    await save_global_settings_doc({"key": "email_settings"}, update_doc)
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "update", "email_settings", None,
        {
            "resend_from_email": resend_from_email,
            "resend_enabled": has_resend,
            "smtp_host": smtp_host,
            "smtp_from_email": smtp_from_email,
            "smtp_use_tls": data.smtp_use_tls,
        },
        ip_address=current_user.get("_ip_address")
    )
    return {"message": "Email settings updated successfully"}


@router.post("/email-settings/test-resend")
async def send_resend_test_email(
    data: EmailTestRequest,
    current_user: dict = Depends(require_admin)
):
    return await _send_email_settings_test(
        provider_key="primary",
        to_email=data.email,
        current_user=current_user,
    )


@router.post("/email-settings/test-smtp")
async def send_smtp_test_email(
    data: EmailTestRequest,
    current_user: dict = Depends(require_admin)
):
    return await _send_email_settings_test(
        provider_key="fallback",
        to_email=data.email,
        current_user=current_user,
    )


# ─── Security Settings (JWT & Backup) ───────────────────────────────────────

@router.get("/security-settings", response_model=SecuritySettingsResponse)
async def get_security_settings(current_user: dict = Depends(require_admin)):
    """Get current security settings (JWT secret, backup password) - masked."""
    doc = await get_global_settings_doc({"type": "env_settings"}, {"_id": 0})
    
    def mask(val):
        if not val: return ""
        return val[:8] + "****" if len(val) > 8 else "****"

    if doc:
        return SecuritySettingsResponse(
            jwt_secret_preview=mask(doc.get("jwt_secret")),
            backup_password_preview=mask(doc.get("backup_password")),
            is_configured=True
        )
    
    # Fallback to env vars
    return SecuritySettingsResponse(
        jwt_secret_preview=mask(os.environ.get("JWT_SECRET")),
        backup_password_preview=mask(os.environ.get("BACKUP_PASSWORD")),
        is_configured=False
    )


@router.put("/security-settings")
async def update_security_settings(
    data: SecuritySettingsUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update security settings (JWT secret, backup password) in DB."""
    now = datetime.now(timezone.utc)
    existing = await get_global_settings_doc({"type": "env_settings"}, {"_id": 0}) or {}
    
    # Merge new data with existing DB settings
    update_doc = {
        "type": "env_settings",
        "updated_at": now.isoformat(),
        "updated_by": current_user["id"],
    }
    
    # Only update fields that are provided
    for field in ["jwt_secret", "backup_password"]:
        val = getattr(data, field)
        if val is not None:
            update_doc[field] = val.strip() if isinstance(val, str) else val
        elif field in existing:
            update_doc[field] = existing[field]
    
    # Preserve other env settings
    for key in ["razorpay_key_id", "razorpay_key_secret", "resend_api_key", "resend_from_email",
                "whatsapp_phone_number_id", "whatsapp_access_token", "whatsapp_business_account_id"]:
        if key in existing:
            update_doc[key] = existing[key]
    
    await save_global_settings_doc({"type": "env_settings"}, update_doc)
    
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "update", "security_settings", None,
        {"updated_fields": [k for k in ["jwt_secret", "backup_password"] if getattr(data, k)]},
        ip_address=current_user.get("_ip_address")
    )
    
    return {"message": "Security settings updated successfully"}


# ─── Env Settings (Legacy/Deprecated - kept for backward compatibility) ───────────────────────────────────────

@router.get("/env-settings", response_model=AdminEnvSettingsResponse)
async def get_env_settings(current_user: dict = Depends(require_admin)):
    """Get current sensitive environment variables stored in DB (masked)."""
    doc = await get_global_settings_doc({"type": "env_settings"}, {"_id": 0})
    
    def mask(val):
        if not val: return ""
        return val[:8] + "****" if len(val) > 8 else "****"

    if doc:
        return AdminEnvSettingsResponse(
            jwt_secret_preview=mask(doc.get("jwt_secret")),
            backup_password_preview=mask(doc.get("backup_password")),
            razorpay_key_id_preview=mask(doc.get("razorpay_key_id")),
            razorpay_key_secret_preview=mask(doc.get("razorpay_key_secret")),
            resend_api_key_preview=mask(doc.get("resend_api_key")),
            resend_from_email=doc.get("resend_from_email") or "",
            whatsapp_phone_number_id=doc.get("whatsapp_phone_number_id") or "",
            whatsapp_access_token_preview=mask(doc.get("whatsapp_access_token")),
            whatsapp_business_account_id=doc.get("whatsapp_business_account_id") or "",
            is_configured=True
        )
    
    # Fallback to env vars
    return AdminEnvSettingsResponse(
        jwt_secret_preview=mask(os.environ.get("JWT_SECRET")),
        backup_password_preview=mask(os.environ.get("BACKUP_PASSWORD")),
        razorpay_key_id_preview=mask(os.environ.get("RAZORPAY_KEY_ID")),
        razorpay_key_secret_preview=mask(os.environ.get("RAZORPAY_KEY_SECRET")),
        resend_api_key_preview=mask(os.environ.get("RESEND_API_KEY")),
        resend_from_email=os.environ.get("RESEND_FROM_EMAIL") or "",
        whatsapp_phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or "",
        whatsapp_access_token_preview=mask(os.environ.get("WHATSAPP_ACCESS_TOKEN")),
        whatsapp_business_account_id=os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID") or "",
        is_configured=False
    )


@router.put("/env-settings")
async def update_env_settings(
    data: EnvSettingsUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update sensitive environment variables in DB."""
    now = datetime.now(timezone.utc)
    existing = await get_global_settings_doc({"type": "env_settings"}, {"_id": 0}) or {}
    
    # Merge new data with existing DB settings
    update_doc = {
        "type": "env_settings",
        "updated_at": now.isoformat(),
        "updated_by": current_user["id"],
    }
    
    # Only update fields that are provided
    for field in [
        "jwt_secret", "backup_password", "razorpay_key_id", "razorpay_key_secret",
        "resend_api_key", "resend_from_email", "whatsapp_phone_number_id",
        "whatsapp_access_token", "whatsapp_business_account_id"
    ]:
        val = getattr(data, field)
        if val is not None:
            update_doc[field] = val.strip() if isinstance(val, str) else val
        elif field in existing:
            update_doc[field] = existing[field]
    
    await save_global_settings_doc({"type": "env_settings"}, update_doc)
    
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "update", "env_settings", None,
        {"updated_fields": [k for k in update_doc.keys() if k not in ["type", "updated_at", "updated_by"]]},
        ip_address=current_user.get("_ip_address")
    )
    
    return {"message": "Environment settings updated successfully"}

