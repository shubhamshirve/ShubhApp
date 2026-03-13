"""Admin: SaaS Plans, Operators, Settings, Gateways, Addons, Dashboard, Audit, Cron, Reports."""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from database import db
from models import (
    SaaSPlanCreate, SaaSPlanResponse,
    OperatorResponse, OperatorUpdate, AdminOperatorCreate, ExtendSubscriptionRequest,
    GlobalSettingsUpdate, AdminPaymentGatewayConfig,
    AddonCreate, AuditLogResponse,
    UserResponse, TokenResponse,
    WhatsAppConfig, WhatsAppTemplateSettings, WhatsAppTestMessage,
    DiscountCodeCreate, DiscountCodeResponse,
    WhatsAppTemplateCreate, WhatsAppTemplateUpdate,
)
from utils import generate_id, hash_password, create_token
from dependencies import require_admin, get_current_user
from audit import log_audit

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─── Helper ───────────────────────────────────────────────────────────────────

def _parse_operator(o: dict) -> OperatorResponse:
    return OperatorResponse(**{
        **o,
        "created_at": datetime.fromisoformat(o["created_at"]),
        "trial_ends_at": datetime.fromisoformat(o["trial_ends_at"]) if o.get("trial_ends_at") else None,
        "subscription_ends_at": datetime.fromisoformat(o["subscription_ends_at"]) if o.get("subscription_ends_at") else None,
    })


# ─── SaaS Plans ──────────────────────────────────────────────────────────────

@router.post("/saas-plans", response_model=SaaSPlanResponse)
async def create_saas_plan(data: SaaSPlanCreate, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    plan = {
        "id": generate_id(), "name": data.name, "monthly_price": data.monthly_price,
        "max_subscribers": data.max_subscribers, "max_staff": data.max_staff,
        "trial_enabled": data.trial_enabled, "trial_days": data.trial_days,
        "gst_applicable": data.gst_applicable, "included_addons": data.included_addons,
        "status": "active", "created_at": now.isoformat(),
        "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.saas_plans.insert_one(plan)
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                    "create", "saas_plans", None, {"name": data.name, "price": data.monthly_price},
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
        "name": data.name, "monthly_price": data.monthly_price,
        "max_subscribers": data.max_subscribers, "max_staff": data.max_staff,
        "trial_enabled": data.trial_enabled, "trial_days": data.trial_days,
        "gst_applicable": data.gst_applicable, "included_addons": data.included_addons,
        "updated_at": now.isoformat()
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

    operator = {
        "id": operator_id, "company_name": data.company_name, "owner_name": data.owner_name,
        "email": data.email, "phone": data.phone, "gst_number": data.gst_number,
        "charge_gst": data.charge_gst, "bank_account_name": data.bank_account_name,
        "bank_account_number": data.bank_account_number, "bank_ifsc": data.bank_ifsc,
        "bank_name": data.bank_name, "status": data.status, "saas_plan_id": data.saas_plan_id,
        "saas_plan_name": plan["name"], "trial_ends_at": None,
        "subscription_ends_at": subscription_ends_at if data.status == "active" else None,
        "is_read_only": False, "created_at": now.isoformat(),
        "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.operators.insert_one(operator)

    user = {
        "id": user_id, "email": data.email, "name": data.owner_name, "phone": data.phone,
        "password": hash_password(data.password), "role": "operator",
        "operator_id": operator_id, "status": "active",
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
    await db.operators.update_one({"id": operator_id}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})
    await db.users.update_many({"operator_id": operator_id, "deleted_at": None}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})
    await db.subscribers.update_many({"operator_id": operator_id, "deleted_at": None}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})
    await db.operator_plans.update_many({"operator_id": operator_id, "deleted_at": None}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})
    await db.invoices.update_many({"operator_id": operator_id, "deleted_at": None}, {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}})
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
async def impersonate_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    user = await db.users.find_one({"operator_id": operator_id, "role": "operator", "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Operator user not found")
    token = create_token({
        "id": user["id"], "email": user["email"], "role": "operator",
        "operator_id": operator_id, "impersonated_by": current_user["id"]
    })
    return {
        "access_token": token, "token_type": "bearer",
        "operator": {"id": operator_id, "company_name": operator["company_name"], "owner_name": operator["owner_name"]}
    }


@router.post("/return-from-impersonate")
async def return_from_impersonate(current_user: dict = Depends(get_current_user)):
    impersonated_by = current_user.get("impersonated_by")
    if not impersonated_by:
        raise HTTPException(status_code=400, detail="Not impersonating any operator")
    admin_user = await db.users.find_one({"id": impersonated_by, "role": "admin", "deleted_at": None}, {"_id": 0})
    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin user not found")
    token = create_token({"id": admin_user["id"], "email": admin_user["email"], "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}


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
    # Mutual exclusion: payment_gateway and custom_payment_gateway cannot coexist
    if addon_code == "payment_gateway" and "custom_payment_gateway" in existing_addons:
        existing_addons.remove("custom_payment_gateway")
    elif addon_code == "custom_payment_gateway" and "payment_gateway" in existing_addons:
        existing_addons.remove("payment_gateway")
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
    settings = await db.global_settings.find_one({"type": "platform"}, {"_id": 0})
    if not settings:
        return {
            "active_payment_gateway": "razorpay", "notification_enabled": True,
            "auto_invoice_days_before": 3, "late_fee_percentage": 0, "gst_rate": 18
        }
    return settings


@router.put("/settings")
async def update_global_settings(data: GlobalSettingsUpdate, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    settings = {"type": "platform", **data.model_dump(), "updated_at": now.isoformat(), "updated_by": current_user["id"]}
    await db.global_settings.update_one({"type": "platform"}, {"$set": settings}, upsert=True)
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                    "update", "global_settings", None, data.model_dump(),
                    ip_address=current_user.get("_ip_address"))
    return {"message": "Settings updated successfully"}


# ─── Platform WhatsApp Config ─────────────────────────────────────────────────

@router.get("/whatsapp-config")
async def get_platform_whatsapp_config(current_user: dict = Depends(require_admin)):
    config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
    if not config:
        return {"phone_number_id": "", "access_token_preview": "", "business_account_id": "", "is_configured": False}
    # Mask the access_token for display
    token = config.get("access_token", "")
    masked_token = token[:8] + "****" if len(token) > 8 else ("****" if token else "")
    return {
        "phone_number_id": config.get("phone_number_id", ""),
        "access_token_preview": masked_token,
        "business_account_id": config.get("business_account_id", ""),
        "is_configured": bool(token)
    }


@router.put("/whatsapp-config")
async def update_platform_whatsapp_config(data: WhatsAppConfig, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    config = {
        "type": "platform_whatsapp",
        "phone_number_id": data.phone_number_id,
        "access_token": data.access_token,
        "business_account_id": data.business_account_id or "",
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
            "announcement_template": ""
        }
    return {
        "invoice_template": settings.get("invoice_template", ""),
        "reminder_template": settings.get("reminder_template", ""),
        "payment_confirmation_template": settings.get("payment_confirmation_template", ""),
        "announcement_template": settings.get("announcement_template", ""),
    }


@router.put("/whatsapp-template-settings")
async def update_whatsapp_template_settings(data: WhatsAppTemplateSettings, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    settings = {
        "type": "whatsapp_template_settings",
        "invoice_template": data.invoice_template or "",
        "reminder_template": data.reminder_template or "",
        "payment_confirmation_template": data.payment_confirmation_template or "",
        "announcement_template": data.announcement_template or "",
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


# ─── Payment Gateways ────────────────────────────────────────────────────────

@router.post("/payment-gateways")
async def create_admin_payment_gateway(
    data: AdminPaymentGatewayConfig, current_user: dict = Depends(require_admin)
):
    now = datetime.now(timezone.utc)
    gateway = {
        "id": generate_id(), "gateway_type": data.gateway_type,
        "api_key": data.api_key, "api_secret": data.api_secret,
        "webhook_secret": data.webhook_secret, "is_active": data.is_active,
        "operator_id": data.for_operator_id,
        "is_platform_gateway": data.for_operator_id is None,
        "created_by": current_user["id"],
        "created_at": now.isoformat(), "updated_at": now.isoformat()
    }
    await db.payment_gateways.update_one(
        {"operator_id": data.for_operator_id, "gateway_type": data.gateway_type},
        {"$set": gateway}, upsert=True
    )
    return {"message": "Payment gateway configured successfully", "id": gateway["id"]}


@router.get("/payment-gateways")
async def get_admin_payment_gateways(current_user: dict = Depends(require_admin)):
    gateways = await db.payment_gateways.find({}, {"_id": 0, "api_secret": 0}).to_list(100)
    for g in gateways:
        if g.get("api_key"):
            g["api_key"] = g["api_key"][:8] + "****"
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
    service = CronJobService(db)
    results = await service.generate_upcoming_invoices(days_before=3)
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
    from services.cron_service import CronJobService
    service = CronJobService(db)
    return await service.check_subscription_expiry()



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
        "has_payment_button": data.has_payment_button,
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
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
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
    from datetime import timedelta
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



# ─── Settlements ─────────────────────────────────────────────────────────────

@router.get("/settlements/summary")
async def get_settlements_summary(current_user: dict = Depends(require_admin)):
    """Get settlement summary statistics."""
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    start_of_month = now.replace(day=1).strftime("%Y-%m-%d")

    all_settlements = await db.settlements.find({}, {"_id": 0}).to_list(50000)

    total_settled = sum(s["net_settlement"] for s in all_settlements if s["status"] == "completed")
    total_pending = sum(s["net_settlement"] for s in all_settlements if s["status"] == "pending")
    total_platform_fee = sum(s["platform_fee"] for s in all_settlements if s["status"] == "completed")

    today_settlements = [s for s in all_settlements if s["settlement_date"] == today]
    today_amount = sum(s["net_settlement"] for s in today_settlements)
    today_count = len(today_settlements)

    month_settlements = [s for s in all_settlements if s["settlement_date"] >= start_of_month]
    month_amount = sum(s["net_settlement"] for s in month_settlements)
    month_collections = sum(s["total_collections"] for s in month_settlements)
    month_fees = sum(s["platform_fee"] for s in month_settlements)

    pending_count = sum(1 for s in all_settlements if s["status"] == "pending")
    completed_count = sum(1 for s in all_settlements if s["status"] == "completed")
    processing_count = sum(1 for s in all_settlements if s["status"] == "processing")
    failed_count = sum(1 for s in all_settlements if s["status"] == "failed")

    # Get platform fee setting
    global_settings = await db.global_settings.find_one({"type": "platform_settings"}, {"_id": 0})
    platform_fee_pct = float((global_settings or {}).get("platform_fee_percentage", 2))

    return {
        "total_settled": round(total_settled, 2),
        "total_pending": round(total_pending, 2),
        "total_platform_fee": round(total_platform_fee, 2),
        "today_amount": round(today_amount, 2),
        "today_count": today_count,
        "month_amount": round(month_amount, 2),
        "month_collections": round(month_collections, 2),
        "month_fees": round(month_fees, 2),
        "pending_count": pending_count,
        "completed_count": completed_count,
        "processing_count": processing_count,
        "failed_count": failed_count,
        "platform_fee_percentage": platform_fee_pct,
    }


@router.get("/settlements")
async def get_settlements(
    status: Optional[str] = None,
    operator_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    """List settlements with filters and pagination."""
    query = {}
    if status:
        query["status"] = status
    if operator_id:
        query["operator_id"] = operator_id
    if date_from or date_to:
        date_q = {}
        if date_from:
            date_q["$gte"] = date_from
        if date_to:
            date_q["$lte"] = date_to
        query["settlement_date"] = date_q

    total = await db.settlements.count_documents(query)
    skip = (page - 1) * limit
    settlements = await db.settlements.find(query, {"_id": 0}).sort(
        "settlement_date", -1
    ).skip(skip).limit(limit).to_list(limit)

    return {
        "settlements": settlements,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
    }


@router.get("/settlements/{settlement_id}")
async def get_settlement_detail(settlement_id: str, current_user: dict = Depends(require_admin)):
    """Get settlement detail with included invoices."""
    settlement = await db.settlements.find_one({"id": settlement_id}, {"_id": 0})
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")

    # Fetch the invoices in this settlement
    invoices = await db.invoices.find(
        {"id": {"$in": settlement.get("invoice_ids", [])}},
        {"_id": 0, "id": 1, "invoice_number": 1, "subscriber_name": 1,
         "final_amount": 1, "tax_amount": 1, "base_amount": 1, "discount": 1,
         "paid_at": 1, "plan_name": 1}
    ).to_list(1000)

    # Fetch operator bank details
    operator = await db.operators.find_one(
        {"id": settlement["operator_id"], "deleted_at": None},
        {"_id": 0, "bank_account_name": 1, "bank_account_number": 1,
         "bank_ifsc": 1, "bank_name": 1, "company_name": 1, "email": 1, "phone": 1}
    )

    return {
        **settlement,
        "invoices": invoices,
        "operator_details": operator,
    }


@router.put("/settlements/{settlement_id}/status")
async def update_settlement_status(
    settlement_id: str,
    status: str = Query(..., regex="^(pending|processing|completed|failed)$"),
    utr_number: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    """Update settlement status (e.g., mark as completed with UTR)."""
    settlement = await db.settlements.find_one({"id": settlement_id}, {"_id": 0})
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")

    now = datetime.now(timezone.utc)
    update = {"status": status, "updated_at": now.isoformat()}
    if status == "completed":
        update["paid_at"] = now.isoformat()
        if utr_number:
            update["utr_number"] = utr_number
    elif status == "processing":
        pass
    elif status == "failed":
        # Un-settle the invoices so they can be re-processed
        await db.invoices.update_many(
            {"id": {"$in": settlement.get("invoice_ids", [])}},
            {"$set": {"settled": False}, "$unset": {"settlement_id": ""}}
        )

    await db.settlements.update_one({"id": settlement_id}, {"$set": update})
    updated = await db.settlements.find_one({"id": settlement_id}, {"_id": 0})
    return updated


@router.post("/settlements/process")
async def trigger_settlement_processing(
    settlement_date: Optional[str] = Query(None, description="Date to process (YYYY-MM-DD). Defaults to yesterday."),
    current_user: dict = Depends(require_admin),
):
    """Manually trigger settlement processing for a specific date."""
    import uuid

    now = datetime.now(timezone.utc)
    if settlement_date:
        try:
            target_date = datetime.strptime(settlement_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    settlement_date_str = target_date.strftime("%Y-%m-%d")
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Get platform fee percentage
    global_settings = await db.global_settings.find_one({"type": "platform_settings"}, {"_id": 0})
    platform_fee_pct = float((global_settings or {}).get("platform_fee_percentage", 2))

    # Find all paid invoices for that date that aren't settled
    paid_invoices = await db.invoices.find({
        "status": "paid",
        "deleted_at": None,
        "settled": {"$ne": True},
        "paid_at": {
            "$gte": start_of_day.isoformat(),
            "$lte": end_of_day.isoformat(),
        },
    }, {"_id": 0}).to_list(10000)

    if not paid_invoices:
        return {"message": f"No unsettled paid invoices found for {settlement_date_str}", "settlements_created": 0}

    # Group by operator
    operator_groups = {}
    for inv in paid_invoices:
        op_id = inv["operator_id"]
        if op_id not in operator_groups:
            operator_groups[op_id] = []
        operator_groups[op_id].append(inv)

    settlements_created = 0
    for operator_id, invoices in operator_groups.items():
        operator = await db.operators.find_one(
            {"id": operator_id, "deleted_at": None}, {"_id": 0}
        )
        if not operator:
            continue

        total_collected = sum(inv["final_amount"] for inv in invoices)
        platform_fee = round(total_collected * platform_fee_pct / 100, 2)
        tax_on_fee = round(platform_fee * 18 / 100, 2)
        net_settlement = round(total_collected - platform_fee - tax_on_fee, 2)
        invoice_ids = [inv["id"] for inv in invoices]

        settlement = {
            "id": str(uuid.uuid4()),
            "operator_id": operator_id,
            "operator_name": operator.get("company_name", "Unknown"),
            "settlement_date": settlement_date_str,
            "total_collections": total_collected,
            "platform_fee_percentage": platform_fee_pct,
            "platform_fee": platform_fee,
            "tax_on_platform_fee": tax_on_fee,
            "net_settlement": net_settlement,
            "payment_count": len(invoices),
            "invoice_ids": invoice_ids,
            "status": "pending",
            "utr_number": None,
            "paid_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        await db.settlements.insert_one(settlement)

        await db.invoices.update_many(
            {"id": {"$in": invoice_ids}},
            {"$set": {"settled": True, "settlement_id": settlement["id"]}}
        )
        settlements_created += 1

    return {
        "message": f"Settlement processing completed for {settlement_date_str}",
        "settlements_created": settlements_created,
        "invoices_processed": len(paid_invoices),
    }


@router.put("/settlements/platform-fee")
async def update_platform_fee(
    percentage: float = Query(..., ge=0, le=50),
    current_user: dict = Depends(require_admin),
):
    """Update the platform fee percentage for settlements."""
    await db.global_settings.update_one(
        {"type": "platform_settings"},
        {"$set": {"platform_fee_percentage": percentage, "type": "platform_settings"}},
        upsert=True,
    )
    return {"message": f"Platform fee updated to {percentage}%", "platform_fee_percentage": percentage}
