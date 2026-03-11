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
        "notification_module": data.notification_module, "auto_reminder": data.auto_reminder,
        "audit_logs": data.audit_logs, "payment_gateway_setup": data.payment_gateway_setup,
        "gst_applicable": data.gst_applicable, "included_addons": data.included_addons,
        "status": "active", "created_at": now.isoformat(),
        "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.saas_plans.insert_one(plan)
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                    "create", "saas_plans", None, {"name": data.name})
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
        "notification_module": data.notification_module, "auto_reminder": data.auto_reminder,
        "audit_logs": data.audit_logs, "payment_gateway_setup": data.payment_gateway_setup,
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
    return [_parse_operator(o) for o in ops]


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
        {"company_name": data.company_name, "email": data.email, "plan": plan["name"]}
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
        {"new_expiry": new_expiry, "months": data.months}
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
        {"deleted_at": deleted_at}
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
                    "delete", "addons", {"addon_id": addon_id}, {})
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
    existing_addons = operator.get("active_addons", [])
    if addon_code not in existing_addons:
        existing_addons.append(addon_code)
    await db.operators.update_one(
        {"id": operator_id},
        {"$set": {"active_addons": existing_addons, "updated_at": now.isoformat()}}
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
                    "update", "global_settings", None, data.model_dump())
    return {"message": "Settings updated successfully"}


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

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_all_audit_logs(
    skip: int = 0, limit: int = 50, current_user: dict = Depends(require_admin)
):
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    result = []
    for log in logs:
        try:
            if isinstance(log.get("old_value"), str):
                log["old_value"] = {"value": log["old_value"]}
            if isinstance(log.get("new_value"), str):
                log["new_value"] = {"value": log["new_value"]}
            log["created_at"] = datetime.fromisoformat(log["created_at"])
            result.append(AuditLogResponse(**log))
        except Exception:
            continue
    return result


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
        query.setdefault("created_at", {})["$lte"] = end_date

    payments = await db.saas_payments.find(query, {"_id": 0}).to_list(1000)
    total = sum(p.get("total_amount", 0) for p in payments)
    gst = sum(p.get("gst_amount", 0) for p in payments)
    plan_counts = {}
    for p in payments:
        plan_id = p.get("saas_plan_id")
        if plan_id not in plan_counts:
            plan_counts[plan_id] = {"count": 0, "revenue": 0}
        plan_counts[plan_id]["count"] += 1
        plan_counts[plan_id]["revenue"] += p.get("total_amount", 0)

    return {
        "total_payments": len(payments), "total_revenue": round(total, 2),
        "total_gst": round(gst, 2), "by_plan": plan_counts
    }


# ─── Cron Triggers ───────────────────────────────────────────────────────────

@router.post("/cron/generate-invoices")
async def trigger_invoice_generation(current_user: dict = Depends(require_admin)):
    from services.cron_service import CronJobService
    service = CronJobService(db)
    results = await service.generate_upcoming_invoices(days_before=5)
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "trigger", "cron_jobs", None, {"action": "generate_invoices", "results": results}
    )
    return results


@router.post("/cron/send-reminders")
async def trigger_reminders(current_user: dict = Depends(require_admin)):
    from services.cron_service import CronJobService
    service = CronJobService(db)
    return await service.send_overdue_reminders(days_overdue=1)


@router.post("/cron/check-expiry")
async def trigger_expiry_check(current_user: dict = Depends(require_admin)):
    from services.cron_service import CronJobService
    service = CronJobService(db)
    return await service.check_subscription_expiry()
