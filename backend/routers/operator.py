"""Operator router: profile, plans, subscribers, invoices, staff, reports, subscription, checkout, etc."""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Request
from fastapi.responses import Response
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import os
import csv
import io
import logging
import uuid

from database import db
from models import (
    OperatorResponse, OperatorUpdate, InvoiceCustomization,
    AnnouncementCreate, OperatorPlanCreate, OperatorPlanResponse,
    SubscriberCreate, SubscriberResponse,
    InvoiceCreate, InvoiceUpdate, InvoiceStatusUpdate, InvoiceResponse, PaymentLinkResponse,
    StaffCreate, StaffUpdate, StaffResponse, AuditLogResponse,
    PaymentGatewayConfig, SendNotificationRequest, BulkNotificationRequest,
    ReminderSettingsUpdate,
)
from utils import generate_id, hash_password, generate_invoice_number, generate_invoice_number_atomic
from dependencies import (
    require_operator,
    require_operator_no_staff,
    check_operator_read_only,
    get_operator_access_state,
)
from audit import log_audit
from sanitization import sanitize_filename, sanitize_text
from services.invoice_view_service import normalize_invoice_settings, build_public_invoice_url, build_public_invoice_path
from routers.wallet import get_or_create_wallet, deduct_wallet

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/operator", tags=["Operator"])
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Addon helper ──────────────────────────────────────────────────────────────

async def _has_addon(operator_id: str, addon_code: str) -> bool:
    """Check if operator has an addon via their SaaS plan or purchased addons."""
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        return False
    if addon_code in operator.get("active_addons", []):
        return True
    plan_id = operator.get("saas_plan_id")
    if plan_id:
        plan = await db.saas_plans.find_one({"id": plan_id, "deleted_at": None}, {"_id": 0})
        if plan and addon_code in plan.get("included_addons", []):
            return True
    return False


async def _get_platform_whatsapp_config():
    """Get the global platform WhatsApp config from admin settings."""
    config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
    if not config or not config.get("access_token"):
        return None
    return config


async def _get_whatsapp_template_settings():
    """Get template assignment settings from admin config."""
    settings = await db.global_settings.find_one({"type": "whatsapp_template_settings"}, {"_id": 0})
    return settings or {}



# ─── Profile ─────────────────────────────────────────────────────────────────

def _parse_operator(o: dict) -> OperatorResponse:
    return OperatorResponse(**{
        **o,
        "created_at": datetime.fromisoformat(o["created_at"]),
        "trial_ends_at": datetime.fromisoformat(o["trial_ends_at"]) if o.get("trial_ends_at") else None,
        "subscription_ends_at": datetime.fromisoformat(o["subscription_ends_at"]) if o.get("subscription_ends_at") else None,
    })


# ─── Features endpoint ────────────────────────────────────────────────────────

@router.get("/features")
async def get_operator_features(current_user: dict = Depends(require_operator)):
    """Return which addon features are active for this operator."""
    if current_user["role"] == "admin":
        return {code: True for code in [
            "audit_log", "payment_gateway",
            "announcement", "whatsapp_notifications",
            "staff_management"
        ]}
    operator_id = current_user["operator_id"]
    addon_codes = [
        "audit_log", "payment_gateway",
        "announcement", "whatsapp_notifications",
        "staff_management"
    ]
    result = {code: await _has_addon(operator_id, code) for code in addon_codes}
    return result


@router.get("/profile", response_model=OperatorResponse)
async def get_operator_profile(current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin users don't have operator profile")
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    return _parse_operator(operator)


@router.put("/profile", response_model=OperatorResponse)
async def update_operator_profile(data: OperatorUpdate, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin users don't have operator profile")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode. Please renew subscription.")

    raw = data.model_dump()
    explicitly_set = data.model_fields_set  # fields actually sent in request body

    # Build update: only include fields that were explicitly sent
    update_data = {}
    for k, v in raw.items():
        if k in explicitly_set:
            update_data[k] = v  # could be None (for clearing), or a real value

    update_data.pop("status", None)

    # GST validation: cannot enable charge_gst without a valid GST number
    if update_data.get("charge_gst") is True:
        # Check if a valid gst_number will exist after this update
        new_gst = update_data.get("gst_number") if "gst_number" in update_data else None
        if new_gst:
            pass  # new valid GST provided in this update
        elif "gst_number" in update_data and not new_gst:
            # Explicitly clearing gst_number while enabling GST - not allowed
            raise HTTPException(
                status_code=400,
                detail="Cannot enable GST charging without a valid GSTIN. Please add your GST number first."
            )
        else:
            # gst_number not in update, check existing DB
            existing = await db.operators.find_one(
                {"id": current_user["operator_id"]}, {"_id": 0, "gst_number": 1}
            )
            if not (existing and existing.get("gst_number")):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot enable GST charging without a valid GSTIN. Please add your GST number first."
                )

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.operators.update_one({"id": current_user["operator_id"]}, {"$set": update_data})
    updated = await db.operators.find_one({"id": current_user["operator_id"]}, {"_id": 0})
    return _parse_operator(updated)


# ─── Invoice Settings ───────────────────────────────────────────────────────

@router.get("/invoice-settings")
async def get_invoice_settings(current_user: dict = Depends(require_operator)):
    settings = await db.invoice_settings.find_one({"operator_id": current_user["operator_id"]}, {"_id": 0})
    operator = await db.operators.find_one({"id": current_user["operator_id"]}, {"_id": 0})
    if not settings:
        return normalize_invoice_settings({}, operator)
    return normalize_invoice_settings(settings, operator)


@router.put("/invoice-settings")
async def update_invoice_settings(data: InvoiceCustomization, current_user: dict = Depends(require_operator)):
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    now = datetime.now(timezone.utc)
    settings = {"operator_id": current_user["operator_id"], **data.model_dump(), "updated_at": now.isoformat()}
    await db.invoice_settings.update_one(
        {"operator_id": current_user["operator_id"]}, {"$set": settings}, upsert=True
    )
    return {"message": "Invoice settings updated"}


@router.post("/invoice-settings/upload-logo")
async def upload_invoice_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_operator),
):
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")

    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, and SVG images are allowed")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")

    safe_original = sanitize_filename(file.filename or "invoice-logo.png", default="invoice-logo")
    ext = safe_original.split(".")[-1].lower() if "." in safe_original else "png"
    filename = f"invoice_logo_{current_user['operator_id']}_{uuid.uuid4().hex[:8]}.{ext}"
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filepath = os.path.join(UPLOAD_DIR, filename)

    try:
        with open(filepath, "wb") as f:
            f.write(content)
        logger.info(f"Logo uploaded successfully to {filepath}")
    except IOError as e:
        logger.error(f"Failed to save logo to {filepath}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save logo: {str(e)}")

    public_url = f"/uploads/{filename}"
    await db.invoice_settings.update_one(
        {"operator_id": current_user["operator_id"]},
        {"$set": {
            "operator_id": current_user["operator_id"],
            "logo_url": public_url,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    await log_audit(
        current_user["id"],
        current_user["name"],
        current_user["role"],
        "upload",
        "invoice_logo",
        None,
        {"filename": filename, "url": public_url, "filepath": filepath},
        ip_address=current_user.get("_ip_address"),
        operator_id=current_user["operator_id"],
    )
    return {"message": "Logo uploaded successfully", "url": public_url, "filename": filename}


# ─── Theme Settings ─────────────────────────────────────────────────────────

@router.get("/theme-settings")
async def get_theme_settings(current_user: dict = Depends(require_operator)):
    """Get theme settings for the operator."""
    settings = await db.operator_theme.find_one(
        {"operator_id": current_user["operator_id"]}, {"_id": 0}
    )
    if not settings:
        # Return default based on plan
        operator = await db.operators.find_one({"id": current_user["operator_id"]}, {"_id": 0})
        is_pro = operator and operator.get("saas_plan_name", "").lower() in ["pro", "professional", "enterprise"]
        return {"theme": "classic" if is_pro else "modern", "operator_id": current_user["operator_id"]}
    return settings


@router.put("/theme-settings")
async def update_theme_settings(theme: str, current_user: dict = Depends(require_operator)):
    """Update theme settings for the operator."""
    theme = sanitize_text(theme)
    if theme not in ["modern", "classic"]:
        raise HTTPException(status_code=400, detail="Invalid theme. Choose 'modern' or 'classic'")
    now = datetime.now(timezone.utc)
    await db.operator_theme.update_one(
        {"operator_id": current_user["operator_id"]},
        {"$set": {"operator_id": current_user["operator_id"], "theme": theme, "updated_at": now.isoformat()}},
        upsert=True
    )
    return {"message": f"Theme updated to {theme}", "theme": theme}


# ─── Announcements ─────────────────────────────────────────────────────────

@router.post("/announcements")
async def create_announcement(data: AnnouncementCreate, current_user: dict = Depends(require_operator)):
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")

    # Check announcement addon
    if not await _has_addon(current_user["operator_id"], "announcement"):
        raise HTTPException(status_code=403, detail="Announcement add-on is not enabled for your plan.")

    # Enforce max 6 announcements per week
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_count = await db.announcements.count_documents({
        "operator_id": current_user["operator_id"],
        "created_at": {"$gte": week_start}
    })
    if week_count >= 6:
        raise HTTPException(status_code=429, detail="Weekly announcement limit reached (max 6 per week).")

    if data.send_to_all:
        subscribers = await db.subscribers.find(
            {"operator_id": current_user["operator_id"], "status": "active", "deleted_at": None}, {"_id": 0}
        ).to_list(10000)
    else:
        subscribers = await db.subscribers.find(
            {"id": {"$in": data.subscriber_ids or []}, "operator_id": current_user["operator_id"], "deleted_at": None},
            {"_id": 0}
        ).to_list(10000)

    announcement = {
        "id": generate_id(), "operator_id": current_user["operator_id"],
        "title": data.title, "message": data.message,
        "recipient_count": len(subscribers), "sent_via_whatsapp": data.send_whatsapp,
        "sent_via_email": data.send_email,
        "created_by": current_user["id"], "created_at": now.isoformat()
    }
    await db.announcements.insert_one(announcement)
    announcement.pop("_id", None)

    sent_count = 0
    whatsapp_count = 0
    email_count = 0
    
    # Get WhatsApp template settings for announcements
    wa_config = await _get_platform_whatsapp_config()
    template_settings = await _get_whatsapp_template_settings()
    announcement_template = template_settings.get("announcement_template", "") if template_settings else ""
    use_template = bool(wa_config and announcement_template)
    
    # Send WhatsApp notifications if enabled
    if data.send_whatsapp:
        if use_template:
            # Use WhatsApp template for announcements
            from services.whatsapp_service import WhatsAppService, resolve_template_variables
            
            # Get template details
            tmpl_doc = await db.whatsapp_templates.find_one(
                {"template_name": announcement_template, "deleted_at": None}, {"_id": 0}
            )
            
            if tmpl_doc:
                wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
                body_vars = tmpl_doc.get("body_variables", [])
                hdr_type = tmpl_doc.get("header_type", "none")
                hdr_params = None
                
                # Handle image header
                if hdr_type == "image":
                    fixed_url = tmpl_doc.get("header_image_url", "")
                    if fixed_url:
                        hdr_params = [fixed_url]
                
                # Send to each subscriber using template
                operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
                
                for sub in subscribers:
                    if sub.get("whatsapp_number"):
                        try:
                            # Create announcement dict for variable resolution
                            announcement_data = {
                                "title": data.title,
                                "message": data.message,
                                "operator_id": current_user["operator_id"],
                                "_operator": operator  # Inject operator for operator_* variables
                            }
                            
                            # Resolve template variables
                            res = await resolve_template_variables(db, body_vars, announcement_data, sub)
                            variables = res["body"]
                            
                            # Send template message
                            result = await wa_service.send_template_message(
                                recipient_phone=sub["whatsapp_number"],
                                template_name=announcement_template,
                                language_code=tmpl_doc.get("language_code", "en"),
                                variables=variables,
                                header_params=hdr_params,
                                header_type=hdr_type,
                            )
                            
                            if result:
                                whatsapp_count += 1
                                logger.info(f"Sent announcement via template to {sub['whatsapp_number']}")
                        except Exception as e:
                            logger.error(f"Failed to send announcement template to {sub['whatsapp_number']}: {e}")
            else:
                logger.warning(f"Announcement template '{announcement_template}' not found, falling back to queue")
                use_template = False
        
        # Fallback: Queue plain text messages (original behavior)
        if not use_template:
            for sub in subscribers:
                if sub.get("whatsapp_number"):
                    notification = {
                        "id": generate_id(), "operator_id": current_user["operator_id"],
                        "subscriber_id": sub["id"], "notification_type": "announcement",
                        "whatsapp_number": sub["whatsapp_number"],
                        "message": f"*{data.title}*\n\n{data.message}",
                        "status": "pending", "created_at": now.isoformat()
                    }
                    await db.notification_queue.insert_one(notification)
                    whatsapp_count += 1
    
    # Send emails if enabled
    if data.send_email:
        try:
            settings = await db.global_settings.find_one({"type": "platform"}, {"_id": 0})
            resend_api_key = (settings or {}).get("resend_api_key", "")
            resend_from_email = (settings or {}).get("resend_from_email", "")
            
            if resend_api_key and resend_from_email:
                from services.email_service import ResendEmailService
                email_service = ResendEmailService(resend_api_key, resend_from_email)
                
                for sub in subscribers:
                    if sub.get("email"):
                        try:
                            html_content = f"""
                            <h2>{data.title}</h2>
                            <p>{data.message}</p>
                            <hr>
                            <p style="font-size: 12px; color: #666;">
                                This is an announcement from your operator. 
                                If you no longer wish to receive these emails, please contact your operator.
                            </p>
                            """
                            await email_service.send_email(
                                to_email=sub["email"],
                                subject=f"Announcement: {data.title}",
                                html=html_content,
                                text=f"{data.title}\n\n{data.message}"
                            )
                            email_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to send email to {sub['email']}: {e}")
        except Exception as e:
            logger.warning(f"Email service unavailable for announcements: {e}")

    return {
        "message": "Announcement created", 
        "recipients": len(subscribers), 
        "whatsapp_sent": whatsapp_count,
        "email_sent": email_count,
    }


@router.get("/announcements")
async def get_announcements(current_user: dict = Depends(require_operator)):
    announcements = await db.announcements.find(
        {"operator_id": current_user["operator_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Calculate weekly limit status
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_count = await db.announcements.count_documents({
        "operator_id": current_user["operator_id"],
        "created_at": {"$gte": week_start}
    })
    
    return {
        "announcements": announcements,
        "weekly_limit": 6,
        "this_week_count": week_count,
        "remaining_this_week": max(0, 6 - week_count)
    }


# ─── Addon Store & Subscription & Checkout ──────────────────────────────────────

@router.get("/addons/store")
async def get_addon_store(current_user: dict = Depends(require_operator)):
    # Block pure admin (not impersonating)
    if current_user["role"] == "admin" and not current_user.get("impersonated_by"):
        raise HTTPException(status_code=400, detail="Admin does not purchase addons")
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    all_addons = await db.addons.find({"deleted_at": None}, {"_id": 0}).to_list(100)
    active = operator.get("active_addons", [])
    addon_expiry = operator.get("addon_expiry", {})
    plan_addons = []
    if operator.get("saas_plan_id"):
        plan = await db.saas_plans.find_one({"id": operator["saas_plan_id"], "deleted_at": None}, {"_id": 0})
        if plan:
            plan_addons = plan.get("included_addons", [])
    result = []
    for addon in all_addons:
        status = "available"
        expires_at = None
        if addon["code"] in active:
            status = "purchased"
            expires_at = addon_expiry.get(addon["code"])
        elif addon["code"] in plan_addons:
            status = "included_in_plan"
            expires_at = operator.get("subscription_ends_at")
        result.append({
            "id": addon["id"], "name": addon["name"], "code": addon["code"],
            "price": addon["price"], "description": addon.get("description", ""),
            "status": status, "expires_at": expires_at
        })
    return result


@router.post("/checkout/validate-coupon")
async def validate_coupon(
    code: str, amount: float,
    current_user: dict = Depends(require_operator)
):
    """Validate a discount code and return the discount amount."""
    if current_user["role"] == "admin" and not current_user.get("impersonated_by"):
        raise HTTPException(status_code=400, detail="Admin cannot use coupons")
    now = datetime.now(timezone.utc)
    doc = await db.discount_codes.find_one({"code": code.upper(), "deleted_at": None}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Invalid discount code")
    if not doc.get("is_active", True):
        raise HTTPException(status_code=400, detail="Discount code is inactive")
    if doc.get("expiry_date"):
        expiry = datetime.fromisoformat(doc["expiry_date"])
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if now > expiry:
            raise HTTPException(status_code=400, detail="Discount code has expired")
    max_r = doc.get("max_redemptions", 0)
    if max_r > 0 and doc.get("used_count", 0) >= max_r:
        raise HTTPException(status_code=400, detail="Discount code redemption limit reached")
    # Per-operator: each operator can only use a coupon once in their lifetime
    operator_id = current_user.get("operator_id", "")
    if operator_id and operator_id in doc.get("redeemed_by", []):
        raise HTTPException(status_code=400, detail="You have already used this discount code")
    # Calculate discount
    if doc["discount_type"] == "percentage":
        discount_amount = round(amount * doc["discount_value"] / 100, 2)
    else:
        discount_amount = min(doc["discount_value"], amount)
    final_amount = max(0, amount - discount_amount)
    return {
        "valid": True,
        "code": doc["code"],
        "discount_type": doc["discount_type"],
        "discount_value": doc["discount_value"],
        "discount_amount": discount_amount,
        "final_amount": final_amount,
        "message": f"{'{}%'.format(int(doc['discount_value'])) if doc['discount_type'] == 'percentage' else '₹{}'.format(int(doc['discount_value']))} discount applied!"
    }


@router.post("/checkout/create-order")
async def create_checkout_order(
    item_type: str, item_code: str = "", months: int = 1, plan_id: str = "",
    addon_codes: str = "", coupon_code: str = "",
    current_user: dict = Depends(require_operator)
):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot checkout")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    settings = await db.global_settings.find_one({"type": "platform"}, {"_id": 0})
    gst_rate = settings.get("gst_rate", 18) if settings else 18
    description = base_amount = receipt_prefix = ""
    base_amount = 0
    selected_addon_codes = [c.strip() for c in addon_codes.split(",") if c.strip()] if addon_codes else []

    if item_type == "addon":
        # Block addon purchase on trial plan
        if operator.get("status") == "trial":
            raise HTTPException(status_code=403, detail="Please subscribe to a paid plan to purchase add-ons.")
        addon = await db.addons.find_one({"code": item_code, "deleted_at": None}, {"_id": 0})
        if not addon:
            raise HTTPException(status_code=404, detail="Add-on not found")
        if item_code in operator.get("active_addons", []):
            raise HTTPException(status_code=400, detail="Add-on already active")
        if operator.get("saas_plan_id"):
            sp = await db.saas_plans.find_one({"id": operator["saas_plan_id"], "deleted_at": None}, {"_id": 0})
            if sp and item_code in sp.get("included_addons", []):
                active = operator.get("active_addons", [])
                active.append(item_code)
                await db.operators.update_one({"id": operator["id"]}, {"$set": {"active_addons": active}})
                return {"status": "activated_free", "message": f"{addon['name']} is included in your plan and activated!"}
        base_amount = addon["price"]
        description = f"Add-on: {addon['name']} (Monthly)"
        receipt_prefix = "ADDON"

    elif item_type == "subscription":
        target_plan_id = plan_id or operator.get("saas_plan_id")
        if not target_plan_id:
            raise HTTPException(status_code=400, detail="No plan selected")
        saas_plan = await db.saas_plans.find_one({"id": target_plan_id, "deleted_at": None}, {"_id": 0})
        if not saas_plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Subscription plan logic: Base price is exclusive of GST.
        base_amount = saas_plan["monthly_price"]
        description = f"{saas_plan['name']} — Monthly Subscription"
        selected_addon_codes = []
        receipt_prefix = "SUB"
    else:
        raise HTTPException(status_code=400, detail="Invalid item_type. Use 'addon' or 'subscription'")

    if base_amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    from routers.wallet import get_referral_settings
    referral_settings = await get_referral_settings()

    # Apply referral discount on the first eligible transaction using platform settings.
    referral_discount_amount = 0.0
    if operator.get("referral_discount_eligible") and not operator.get("referral_discount_used"):
        referral_discount_amount = min(
            round(base_amount * referral_settings["referral_discount_percent"] / 100, 2),
            referral_settings["referral_discount_max_amount"],
        )

    # Apply coupon discount (before GST)
    discount_amount = 0.0
    applied_coupon = None
    if coupon_code:
        coupon_doc = await db.discount_codes.find_one({"code": coupon_code.upper(), "deleted_at": None}, {"_id": 0})
        if coupon_doc and coupon_doc.get("is_active"):
            now_check = datetime.now(timezone.utc)
            valid = True
            if coupon_doc.get("expiry_date"):
                exp = datetime.fromisoformat(coupon_doc["expiry_date"])
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now_check > exp:
                    valid = False
            max_r = coupon_doc.get("max_redemptions", 0)
            if max_r > 0 and coupon_doc.get("used_count", 0) >= max_r:
                valid = False
            if valid:
                # Per-operator: each operator can only use a coupon once in their lifetime
                if operator["id"] in coupon_doc.get("redeemed_by", []):
                    valid = False
            if valid:
                if coupon_doc["discount_type"] == "percentage":
                    discount_amount = round(base_amount * coupon_doc["discount_value"] / 100, 2)
                else:
                    discount_amount = min(coupon_doc["discount_value"], base_amount)
                applied_coupon = coupon_code.upper()
    discounted_base = round(base_amount - discount_amount - referral_discount_amount, 2)

    # Calculate GST on the discounted base amount for all SaaS checkout items
    gst_amount = round(discounted_base * gst_rate / 100, 2)
    exact_total = discounted_base + gst_amount
    import math
    rounded_total = math.floor(exact_total + 0.5)          # standard half-up rounding → int
    rounding_diff = round(rounded_total - exact_total, 2)  # +ve = rounded up, -ve = rounded down

    # Use platform payment gateway from DB, fallback to env vars
    platform_gw = await db.payment_gateways.find_one({"is_platform_gateway": True, "is_active": True}, {"_id": 0})
    if platform_gw:
        razorpay_key = platform_gw["api_key"]
        razorpay_secret = platform_gw["api_secret"]
    else:
        razorpay_key = os.environ.get("RAZORPAY_KEY_ID")
        razorpay_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not razorpay_key or not razorpay_secret:
        raise HTTPException(status_code=500, detail="Platform payment gateway not configured. Please contact admin.")

    from services.razorpay_service import RazorpayService
    rz = RazorpayService(razorpay_key, razorpay_secret)
    order_id = generate_id()
    order = rz.create_order(
        amount=rounded_total, receipt=f"{receipt_prefix}-{order_id[:8]}",
        notes={"type": item_type, "item_code": item_code, "plan_id": plan_id,
               "months": str(months), "operator_id": operator["id"], "internal_order_id": order_id}
    )

    now = datetime.now(timezone.utc)
    await db.checkout_orders.insert_one({
        "id": order_id, "razorpay_order_id": order["id"],
        "operator_id": operator["id"], "item_type": item_type,
        "item_code": item_code, "plan_id": plan_id, "months": months,
        "addon_codes": selected_addon_codes,
        "base_amount": base_amount, "discount_amount": discount_amount,
        "referral_discount_amount": referral_discount_amount,
        "discounted_base": discounted_base,
        "gst_amount": gst_amount,
        "exact_total": exact_total, "rounding_diff": rounding_diff,
        "total_amount": rounded_total,
        "coupon_code": applied_coupon,
        "description": description, "status": "created",
        "created_at": now.isoformat(), "deleted_at": None
    })

    platform_name = settings.get("platform_name", "E-Bill") if settings else "E-Bill"
    return {
        "razorpay_order_id": order["id"], "razorpay_key": razorpay_key,
        "amount": rounded_total * 100, "currency": "INR",
        "name": platform_name, "description": description,
        "base_amount": base_amount, "discount_amount": discount_amount,
        "referral_discount_amount": referral_discount_amount,
        "discounted_base": discounted_base,
        "gst_amount": gst_amount,
        "exact_total": exact_total, "rounding_diff": rounding_diff,
        "total_amount": rounded_total,
        "coupon_code": applied_coupon,
        "prefill": {"name": operator.get("owner_name", ""), "email": operator.get("email", ""), "contact": operator.get("phone", "")}
    }


@router.post("/checkout/verify")
async def verify_checkout_payment(
    razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str,
    current_user: dict = Depends(require_operator)
):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot verify checkout")
    platform_gw = await db.payment_gateways.find_one({"is_platform_gateway": True, "is_active": True}, {"_id": 0})
    if platform_gw:
        razorpay_key = platform_gw["api_key"]
        razorpay_secret = platform_gw["api_secret"]
    else:
        razorpay_key = os.environ.get("RAZORPAY_KEY_ID")
        razorpay_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not razorpay_key or not razorpay_secret:
        raise HTTPException(status_code=500, detail="Platform payment gateway not configured. Please contact admin.")

    from services.razorpay_service import RazorpayService
    rz = RazorpayService(razorpay_key, razorpay_secret)
    if not rz.verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment verification failed")

    order = await db.checkout_orders.find_one(
        {"razorpay_order_id": razorpay_order_id, "operator_id": current_user["operator_id"]}, {"_id": 0}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    now = datetime.now(timezone.utc)
    operator = await db.operators.find_one({"id": current_user["operator_id"]}, {"_id": 0})

    if order["item_type"] == "addon":
        active = operator.get("active_addons", [])
        addon_expiry = operator.get("addon_expiry", {})
        new_code = order["item_code"]
        if new_code not in active:
            active.append(new_code)
        # Expiry = current subscription end date
        expiry_date = operator.get("subscription_ends_at") or now.isoformat()
        addon_expiry[new_code] = expiry_date
        await db.operators.update_one(
            {"id": operator["id"]},
            {"$set": {"active_addons": active, "addon_expiry": addon_expiry, "updated_at": now.isoformat()}}
        )
        result_msg = f"Add-on '{new_code}' activated"

    elif order["item_type"] == "subscription":
        from dateutil.relativedelta import relativedelta
        current_end = operator.get("subscription_ends_at")
        start = now
        if current_end:
            start = datetime.fromisoformat(current_end)
            if start < now:
                start = now
        new_end = start + relativedelta(months=order["months"])
        new_end_iso = new_end.isoformat()
        update_fields = {
            "subscription_ends_at": new_end_iso, "status": "active",
            "is_read_only": False, "updated_at": now.isoformat()
        }
        if order.get("plan_id"):
            update_fields["saas_plan_id"] = order["plan_id"]
        # Extend all existing active addons expiry to new subscription end date
        addon_expiry = operator.get("addon_expiry", {})
        active = operator.get("active_addons", [])
        for code in active:
            addon_expiry[code] = new_end_iso
        # Activate any addons bundled with this subscription order
        if order.get("addon_codes"):
            for code in order["addon_codes"]:
                if code not in active:
                    active.append(code)
                    # If staff_management addon, set max_staff = 5
                    if code == "staff_management":
                        update_fields["max_staff"] = 5
                addon_expiry[code] = new_end_iso
            update_fields["active_addons"] = active
        update_fields["addon_expiry"] = addon_expiry
        await db.operators.update_one({"id": operator["id"]}, {"$set": update_fields})
        
        # Credit the operator's wallet with the pre-GST base amount
        from routers.wallet import credit_wallet
        await credit_wallet(
            operator_id=operator["id"],
            amount=order["base_amount"],
            description=f"Subscription Credit: {order['item_code'] or order.get('plan_id', '')}",
            tx_type="subscription_credit"
        )
        
        result_msg = f"Subscription extended by {order['months']} month(s) and wallet credited ₹{order['base_amount']}"
    else:
        result_msg = "Payment verified"

    await db.checkout_orders.update_one(
        {"razorpay_order_id": razorpay_order_id},
        {"$set": {"status": "paid", "razorpay_payment_id": razorpay_payment_id, "paid_at": now.isoformat()}}
    )

    # Increment coupon used_count and record operator if a coupon was applied
    if order.get("coupon_code"):
        await db.discount_codes.update_one(
            {"code": order["coupon_code"]},
            {
                "$inc": {"used_count": 1},
                "$addToSet": {"redeemed_by": operator["id"]}
            }
        )

    payment_record = {
        "id": generate_id(), "operator_id": operator["id"],
        "order_id": order["id"], "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "item_type": order["item_type"], "item_code": order.get("item_code", ""),
        "base_amount": order["base_amount"],
        "discount_amount": order.get("discount_amount", 0),
        "referral_discount_amount": order.get("referral_discount_amount", 0),
        "coupon_code": order.get("coupon_code"),
        "gst_amount": order["gst_amount"],
        "total_amount": order["total_amount"], "status": "completed",
        "created_at": now.isoformat(), "deleted_at": None
    }
    await db.saas_payments.insert_one(payment_record)

    if order["item_type"] == "subscription":
        try:
            from routers.wallet import apply_referral_reward
            # Mark referral discount as used (first transaction)
            if operator.get("referral_discount_eligible") and not operator.get("referral_discount_used"):
                await db.operators.update_one(
                    {"id": operator["id"]},
                    {"$set": {"referral_discount_used": True, "updated_at": now.isoformat()}}
                )
            # Subscription pricing is a flat SaaS fee; only referral reward affects wallet here.
            await apply_referral_reward(operator["id"], order["total_amount"], razorpay_payment_id)
        except Exception as e:
            logger.warning(f"Subscription post-payment wallet updates failed: {e}")

    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "payment", "checkout", None, {"type": order["item_type"], "amount": order["total_amount"]},
        ip_address=current_user.get("_ip_address"),
        operator_id=operator["id"]
    )
    return {"status": "success", "message": result_msg}


@router.get("/subscription")
async def get_operator_subscription(current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin does not have a subscription")
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    access_state = await get_operator_access_state(current_user["operator_id"])
    saas_plan = None
    current_plan_id = operator.get("saas_plan_id")
    
    if current_plan_id:
        saas_plan = await db.saas_plans.find_one({"id": current_plan_id, "deleted_at": None}, {"_id": 0})
    
    available_plans = await db.saas_plans.find({"deleted_at": None, "trial_enabled": False}, {"_id": 0}).to_list(50)
    subscriber_count = await db.subscribers.count_documents(
        {"operator_id": operator["id"], "status": "active", "deleted_at": None}
    )
    
    # Validate that the current plan ID exists in available plans
    plan_id_valid = False
    if current_plan_id and saas_plan:
        # Check if the current plan ID matches one in available plans
        plan_id_valid = any(p["id"] == current_plan_id for p in available_plans)
    
    return {
        "operator_id": operator["id"], "company_name": operator.get("company_name", ""),
        "status": operator.get("status", "unknown"),
        "saas_plan_id": current_plan_id,
        "saas_plan_name": operator.get("saas_plan_name") or (saas_plan["name"] if saas_plan else None),
        "saas_plan_price": saas_plan.get("monthly_price") if saas_plan else None,
        "per_invoice_price": saas_plan.get("per_invoice_price", 10.0) if saas_plan else 10.0,
        "subscriber_count": subscriber_count,
        "subscription_ends_at": operator.get("subscription_ends_at"),
        "trial_ends_at": operator.get("trial_ends_at"),
        "is_read_only": access_state["is_read_only"],
        "maintenance_mode": access_state["maintenance_mode"],
        "maintenance_message": access_state["maintenance_message"],
        "plan_validation": {
            "is_valid": plan_id_valid,
            "current_plan_id": current_plan_id,
            "plan_exists_in_available": plan_id_valid,
        },
        "available_plans": [
            {
                "id": p["id"], "name": p["name"],
                "monthly_price": p.get("monthly_price", 0),
                "per_invoice_price": p.get("per_invoice_price", 10.0),
                "included_addons": p.get("included_addons", []),
            }
            for p in available_plans
        ]
    }


@router.get("/payment-history")
async def get_operator_payment_history(current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin does not have payment history")
    payments = await db.saas_payments.find(
        {"operator_id": current_user["operator_id"], "status": "completed", "deleted_at": None}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return payments


@router.post("/renew-subscription")
async def renew_operator_subscription(
    plan_id: Optional[str] = None, months: int = 1,
    current_user: dict = Depends(require_operator)
):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot renew")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    # Check renewal window: allow renewal from 3 days before expiry until the expiry date
    now = datetime.now(timezone.utc)
    subscription_ends = operator.get("subscription_ends_at") or operator.get("trial_ends_at")
    if subscription_ends:
        if isinstance(subscription_ends, str):
            subscription_ends = datetime.fromisoformat(subscription_ends)
        if subscription_ends.tzinfo is None:
            subscription_ends = subscription_ends.replace(tzinfo=timezone.utc)
        
        # Calculate the renewal window start (3 days before expiry)
        renewal_window_start = subscription_ends - timedelta(days=3)
        
        # Check if current time is within the renewal window
        if now < renewal_window_start:
            days_until_window = (renewal_window_start - now).days
            raise HTTPException(
                status_code=400, 
                detail=f"Renewal is available 3 days before expiry. You can renew in {days_until_window} days."
            )
        if now > subscription_ends:
            # Allow renewal even after expiry
            pass
    
    target_plan_id = plan_id or operator.get("saas_plan_id")
    if not target_plan_id:
        raise HTTPException(status_code=400, detail="No plan selected.")
    saas_plan = await db.saas_plans.find_one({"id": target_plan_id, "deleted_at": None}, {"_id": 0})
    if not saas_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    amount = saas_plan["monthly_price"] * months
    gst_amount = 0
    if saas_plan.get("gst_applicable"):
        settings = await db.global_settings.find_one({"type": "platform"}, {"_id": 0})
        gst_rate = settings.get("gst_rate", 18) if settings else 18
        gst_amount = round(amount * gst_rate / 100, 2)
    import math
    exact_total = round(amount + gst_amount, 2)
    total_amount = math.floor(exact_total + 0.5)           # standard half-up round to int
    rounding_diff = round(total_amount - exact_total, 2)
    renewal_id = generate_id()
    payment_link = None
    razorpay_key = os.environ.get("RAZORPAY_KEY_ID")
    razorpay_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if razorpay_key and razorpay_secret and total_amount > 0:
        try:
            from services.razorpay_service import RazorpayService
            rz = RazorpayService(razorpay_key, razorpay_secret)
            result = rz.create_payment_link(
                amount=total_amount,
                description=f"SaaS Subscription: {saas_plan['name']} x {months} month(s)",
                customer_name=operator.get("owner_name", "Operator"),
                customer_email=operator.get("email", ""),
                customer_phone=operator.get("phone", ""),
                invoice_number=f"SAAS-{renewal_id[:8]}"
            )
            if result:
                payment_link = result.get("short_url")
        except Exception as e:
            logger.warning(f"Razorpay link creation failed: {e}")
    renewal_now = datetime.now(timezone.utc)
    renewal = {
        "id": renewal_id, "operator_id": operator["id"],
        "plan_id": target_plan_id, "plan_name": saas_plan["name"],
        "months": months, "base_amount": amount, "gst_amount": gst_amount,
        "exact_total": exact_total, "rounding_diff": rounding_diff,
        "total_amount": total_amount, "payment_link": payment_link,
        "status": "pending", "created_at": renewal_now.isoformat(), "deleted_at": None
    }
    await db.saas_payments.insert_one(renewal)
    renewal.pop("_id", None)
    return renewal


# ─── Dashboard ──────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_operator_dashboard(current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Use admin dashboard")
    operator_id = current_user["operator_id"]
    total_subscribers = await db.subscribers.count_documents({"operator_id": operator_id, "deleted_at": None})
    active_subscribers = await db.subscribers.count_documents({"operator_id": operator_id, "status": "active", "deleted_at": None})
    total_invoices = await db.invoices.count_documents({"operator_id": operator_id, "deleted_at": None})
    pending_invoices = await db.invoices.count_documents({"operator_id": operator_id, "status": "pending", "deleted_at": None})
    overdue_invoices = await db.invoices.count_documents({"operator_id": operator_id, "status": "overdue", "deleted_at": None})
    paid_invoices = await db.invoices.count_documents({"operator_id": operator_id, "status": "paid", "deleted_at": None})
    cancelled_invoices = await db.invoices.count_documents({"operator_id": operator_id, "status": "cancelled", "deleted_at": None})
    paid_invoice_list = await db.invoices.find(
        {"operator_id": operator_id, "status": "paid", "deleted_at": None}, {"_id": 0, "final_amount": 1}
    ).to_list(1000)
    total_revenue = sum(inv.get("final_amount", 0) for inv in paid_invoice_list)
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    access_state = await get_operator_access_state(operator_id)
    # Fetch plan limits
    max_subscribers = None
    max_staff = None
    if operator and operator.get("saas_plan_id"):
        sp = await db.saas_plans.find_one({"id": operator["saas_plan_id"], "deleted_at": None}, {"_id": 0})
        if sp:
            max_subscribers = sp.get("max_subscribers")
            # Use operator-level max_staff override if set (staff_management addon)
            max_staff = operator.get("max_staff") or sp.get("max_staff")
    current_staff = await db.users.count_documents({"operator_id": operator_id, "role": "staff", "deleted_at": None})
    slots_remaining = max(0, max_subscribers - total_subscribers) if max_subscribers is not None else None

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)

    month_invoice_docs = await db.invoices.find(
        {
            "operator_id": operator_id,
            "deleted_at": None,
            "created_at": {"$gte": month_start.isoformat(), "$lt": next_month_start.isoformat()},
        },
        {"_id": 0, "final_amount": 1, "status": 1}
    ).to_list(5000)
    month_received_docs = await db.invoices.find(
        {
            "operator_id": operator_id,
            "deleted_at": None,
            "status": "paid",
            "paid_at": {"$gte": month_start.isoformat(), "$lt": next_month_start.isoformat()},
        },
        {"_id": 0, "final_amount": 1}
    ).to_list(5000)

    total_invoice_value_this_month = round(sum(inv.get("final_amount", 0) for inv in month_invoice_docs), 2)
    total_value_pending_this_month = round(
        sum(inv.get("final_amount", 0) for inv in month_invoice_docs if inv.get("status") in {"pending", "overdue"}),
        2,
    )
    total_value_received_this_month = round(sum(inv.get("final_amount", 0) for inv in month_received_docs), 2)
    total_pending_value = round(
        sum(inv.get("final_amount", 0) for inv in await db.invoices.find(
            {"operator_id": operator_id, "deleted_at": None, "status": {"$in": ["pending", "overdue"]}},
            {"_id": 0, "final_amount": 1}
        ).to_list(5000)),
        2,
    )
    return {
        "total_subscribers": total_subscribers, "active_subscribers": active_subscribers,
        "total_invoices": total_invoices, "pending_invoices": pending_invoices,
        "overdue_invoices": overdue_invoices, "paid_invoices": paid_invoices,
        "cancelled_invoices": cancelled_invoices,
        "total_revenue": total_revenue,
        "total_invoice_value_this_month": total_invoice_value_this_month,
        "total_value_received_this_month": total_value_received_this_month,
        "total_value_pending_this_month": total_value_pending_this_month,
        "total_pending_value": total_pending_value,
        "is_read_only": access_state["is_read_only"],
        "maintenance_mode": access_state["maintenance_mode"],
        "maintenance_message": access_state["maintenance_message"],
        "subscription_ends_at": operator.get("subscription_ends_at") if operator else None,
        "trial_ends_at": operator.get("trial_ends_at") if operator else None,
        "status": operator.get("status") if operator else "unknown",
        "max_subscribers": max_subscribers,
        "subscriber_slots_remaining": slots_remaining,
        "max_staff": max_staff,
        "current_staff": current_staff,
    }


# ─── Service Plans ──────────────────────────────────────────────────────────

@router.post("/plans", response_model=OperatorPlanResponse)
async def create_operator_plan(data: OperatorPlanCreate, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot create operator plans")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    now = datetime.now(timezone.utc)
    plan = {
        "id": generate_id(), "name": data.name, "price": data.price, "validity": data.validity,
        "tax_percentage": data.tax_percentage, "tax_type": data.tax_type,
        "description": data.description, "status": "active",
        "operator_id": current_user["operator_id"],
        "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.operator_plans.insert_one(plan)
    return OperatorPlanResponse(**{**plan, "created_at": now})


@router.get("/plans", response_model=List[OperatorPlanResponse])
async def get_operator_plans(current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator plans")
    try:
        plans = await db.operator_plans.find(
            {"operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
        ).to_list(100)
        parsed_plans = []
        for p in plans:
            try:
                created_at = p["created_at"]
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                elif not isinstance(created_at, datetime):
                    created_at = datetime.now(timezone.utc)
                
                # Use Pydantic model for validation
                plan_data = {**p, "created_at": created_at}
                parsed_plans.append(OperatorPlanResponse(**plan_data))
            except Exception as e:
                logger.error(f"Error parsing plan {p.get('id', 'unknown')}: {str(e)}")
                # Continue to next plan
                continue
        return parsed_plans
    except Exception as e:
        logger.error(f"Error in get_operator_plans: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving plans: {str(e)}")


# ─── Bulk Upload: Plans ────────────────────────────────────────────────────────

@router.get("/plans/sample-csv")
async def get_plans_sample_csv(current_user: dict = Depends(require_operator)):
    """Download a sample CSV template for bulk plan upload."""
    rows = [
        ["name", "price", "validity", "tax_percentage", "tax_type", "description"],
        ["Monthly Basic",      "500",  "monthly",     "18", "exclusive", "Basic monthly broadband plan"],
        ["Quarterly Standard", "1400", "quarterly",   "18", "exclusive", "Standard quarterly plan"],
        ["Half Yearly Gold",   "2700", "half_yearly",  "0", "none",      "Half yearly plan with no tax"],
        ["Annual Premium",     "5000", "yearly",      "18", "inclusive", "Annual premium plan GST inclusive"],
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plans_sample.csv"}
    )


@router.post("/plans/bulk-upload")
async def bulk_upload_plans(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_operator)
):
    """Bulk upload service plans from a CSV or XLSX file (background job)."""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot upload operator plans")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")

    content = await file.read()
    filename = sanitize_filename(file.filename or "", default="plans").lower()

    from services.job_queue_service import JobQueueService
    job_id = await JobQueueService.enqueue_job(
        job_type="bulk_upload_plans",
        operator_id=current_user["operator_id"],
        user_id=current_user["id"],
        payload={
            "filename": filename,
            "file_content": content,
        }
    )

    return {
        "job_id": job_id,
        "message": "Job queued. Poll /api/operator/jobs/{job_id} to check status.",
        "status_url": f"/api/operator/jobs/{job_id}"
    }


@router.put("/plans/{plan_id}", response_model=OperatorPlanResponse)
async def update_operator_plan(plan_id: str, data: OperatorPlanCreate, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot update operator plans")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    existing = await db.operator_plans.find_one(
        {"id": plan_id, "operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found")
    update_data = data.model_dump()
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.operator_plans.update_one({"id": plan_id}, {"$set": update_data})
    updated = await db.operator_plans.find_one({"id": plan_id}, {"_id": 0})
    return OperatorPlanResponse(**{**updated, "created_at": datetime.fromisoformat(updated["created_at"])})


@router.delete("/plans/{plan_id}")
async def delete_operator_plan(plan_id: str, current_user: dict = Depends(require_operator_no_staff)):
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    result = await db.operator_plans.update_one(
        {"id": plan_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Plan deleted"}


# ─── Subscribers ────────────────────────────────────────────────────────────

@router.post("/subscribers", response_model=SubscriberResponse)
async def create_subscriber(data: SubscriberCreate, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot create subscribers")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if operator:
        plan = await db.saas_plans.find_one({"id": operator.get("saas_plan_id"), "deleted_at": None}, {"_id": 0})
        if plan:
            current_count = await db.subscribers.count_documents({"operator_id": current_user["operator_id"], "deleted_at": None})
            if current_count >= plan["max_subscribers"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"Subscriber limit reached ({current_count}/{plan['max_subscribers']}). Please upgrade your plan to add more subscribers."
                )

    # Validate all plans exist and enrich names
    enriched_plans = []
    for p in data.plans:
        op_plan = await db.operator_plans.find_one(
            {"id": p.plan_id, "operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
        )
        if not op_plan:
            raise HTTPException(status_code=404, detail=f"Plan {p.plan_id} not found")
        
        plan_dict = p.model_dump()
        plan_dict["plan_name"] = op_plan["name"]
        enriched_plans.append(plan_dict)

    now = datetime.now(timezone.utc)
    subscriber = {
        "id": generate_id(), "name": data.name, "whatsapp_number": data.whatsapp_number,
        "email": data.email, "address": data.address,
        "plans": enriched_plans,
        "status": "active", "operator_id": current_user["operator_id"],
        "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.subscribers.insert_one(subscriber)
    return SubscriberResponse(**{**subscriber, "created_at": now})


@router.get("/subscribers", response_model=List[SubscriberResponse])
async def get_subscribers(
    status: Optional[str] = None, plan_id: Optional[str] = None,
    current_user: dict = Depends(require_operator)
):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator subscribers")
    query = {"operator_id": current_user["operator_id"], "deleted_at": None}
    if status:
        query["status"] = status
    if plan_id:
        query["plans.plan_id"] = plan_id
    subscribers = await db.subscribers.find(query, {"_id": 0}).to_list(1000)
    return [SubscriberResponse(**{**s, "created_at": datetime.fromisoformat(s["created_at"])}) for s in subscribers]


@router.get("/subscribers/search")
async def search_subscribers(
    q: str = Query("", description="Search query for name, phone, or email"),
    limit: int = Query(50, ge=1, le=100, description="Max results to return"),
    current_user: dict = Depends(require_operator)
):
    """Search subscribers with server-side filtering (for invoice dropdown, etc.)"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator subscribers")
    
    query = {"operator_id": current_user["operator_id"], "deleted_at": None}
    
    # Add search filter if query provided
    if q.strip():
        search_pattern = {"$regex": q.strip(), "$options": "i"}
        query["$or"] = [
            {"name": search_pattern},
            {"whatsapp_number": search_pattern},
            {"email": search_pattern}
        ]
    
    subscribers = await db.subscribers.find(
        query, 
        {"_id": 0, "id": 1, "name": 1, "whatsapp_number": 1, "email": 1}
    ).sort("name", 1).to_list(limit)
    
    return subscribers


# ─── Bulk Upload: Subscribers ─────────────────────────────────────────────────

@router.get("/subscribers/sample-csv")
async def get_subscribers_sample_csv(current_user: dict = Depends(require_operator)):
    """Download a sample CSV template for bulk subscriber upload."""
    rows = [
        [
            "name", "whatsapp_number", "email", "address",
            "plan_name_1", "billing_date_1", "discount_1",
            "plan_name_2", "billing_date_2", "discount_2",
            "plan_name_3", "billing_date_3", "discount_3",
            "plan_name_4", "billing_date_4", "discount_4",
            "plan_name_5", "billing_date_5", "discount_5",
        ],
        # Single plan example
        ["Rajesh Kumar",  "9876543210", "rajesh@example.com",  "123 MG Road, Mumbai",     "Monthly Basic", "1",  "0",  "",              "",   "",  "", "", "", "", "", "", "", ""],
        # Two plans example
        ["Priya Sharma",  "9123456789", "priya@example.com",   "456 Anna Salai, Chennai", "Monthly Basic", "5",  "0",  "Fiber Pro",     "5",  "0", "", "", "", "", "", "", "", ""],
        # Three plans with discount on first
        ["Amit Patel",    "9988776655", "amit@example.com",    "789 FC Road, Pune",       "Monthly Basic", "10", "50", "Fiber Pro",     "10", "0", "Cable TV", "10", "0", "", "", "", "", ""],
        # Single plan, no email
        ["Sunita Verma",  "9871234567", "",                    "321 Brigade Rd, Bangalore","Monthly Basic", "15", "0",  "",              "",   "",  "", "", "", "", "", "", "", ""],
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=subscribers_sample.csv"}
    )


@router.post("/subscribers/bulk-upload")
async def bulk_upload_subscribers(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_operator)
):
    """Bulk upload subscribers from a CSV or XLSX file (background job)."""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot upload subscribers")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")

    content = await file.read()
    filename = sanitize_filename(file.filename or "", default="subscribers").lower()

    from services.job_queue_service import JobQueueService
    job_id = await JobQueueService.enqueue_job(
        job_type="bulk_upload_subscribers",
        operator_id=current_user["operator_id"],
        user_id=current_user["id"],
        payload={
            "filename": filename,
            "file_content": content,
        }
    )

    return {
        "job_id": job_id,
        "message": "Job queued. Poll /api/operator/jobs/{job_id} to check status.",
        "status_url": f"/api/operator/jobs/{job_id}"
    }


@router.get("/subscribers/{subscriber_id}", response_model=SubscriberResponse)
async def get_subscriber(subscriber_id: str, current_user: dict = Depends(require_operator)):
    subscriber = await db.subscribers.find_one(
        {"id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
    )
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return SubscriberResponse(**{**subscriber, "created_at": datetime.fromisoformat(subscriber["created_at"])})


@router.put("/subscribers/{subscriber_id}", response_model=SubscriberResponse)
async def update_subscriber(subscriber_id: str, data: SubscriberCreate, current_user: dict = Depends(require_operator)):
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    existing = await db.subscribers.find_one(
        {"id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    # Validate all plans exist and enrich names
    enriched_plans = []
    for p in data.plans:
        op_plan = await db.operator_plans.find_one(
            {"id": p.plan_id, "operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
        )
        if not op_plan:
            raise HTTPException(status_code=404, detail=f"Plan {p.plan_id} not found")
        
        plan_dict = p.model_dump()
        plan_dict["plan_name"] = op_plan["name"]
        enriched_plans.append(plan_dict)

    update_data = data.model_dump()
    update_data["plans"] = enriched_plans
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.subscribers.update_one({"id": subscriber_id}, {"$set": update_data})
    updated = await db.subscribers.find_one({"id": subscriber_id}, {"_id": 0})
    return SubscriberResponse(**{**updated, "created_at": datetime.fromisoformat(updated["created_at"])})


@router.delete("/subscribers/{subscriber_id}")
async def delete_subscriber(subscriber_id: str, current_user: dict = Depends(require_operator_no_staff)):
    # Only admin impersonating as operator can delete subscribers
    if not current_user.get("impersonated_by"):
        raise HTTPException(status_code=403, detail="Only admin can delete subscribers. Use suspend instead.")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    # Check for linked invoices that are not cancelled
    linked_invoices = await db.invoices.find(
        {"subscriber_id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None, "status": {"$ne": "cancelled"}}
    ).to_list(None)
    
    if linked_invoices:
        invoice_numbers = ", ".join([inv.get("invoice_number", inv.get("id", "")) for inv in linked_invoices[:5]])
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete subscriber with active invoices. Please cancel these invoices first: {invoice_numbers}"
        )
    
    result = await db.subscribers.update_one(
        {"id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"message": "Subscriber deleted"}


@router.post("/subscribers/{subscriber_id}/suspend")
async def suspend_subscriber(subscriber_id: str, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot suspend subscribers directly")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    result = await db.subscribers.update_one(
        {"id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"$set": {"status": "inactive", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"message": "Subscriber suspended"}


@router.post("/subscribers/{subscriber_id}/activate")
async def activate_subscriber(subscriber_id: str, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot activate subscribers directly")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    result = await db.subscribers.update_one(
        {"id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"$set": {"status": "active", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"message": "Subscriber activated"}


# ─── Invoices ─────────────────────────────────────────────────────────────────

PAYMENT_MODES = {"cash", "own_upi", "bank_transfer", "cheque"}


async def _build_invoice_payload(operator_id: str, data: InvoiceCreate | InvoiceUpdate):
    subscriber = await db.subscribers.find_one(
        {"id": data.subscriber_id, "operator_id": operator_id, "deleted_at": None}, {"_id": 0}
    )
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    can_charge_gst = operator.get("charge_gst") and operator.get("gst_number")

    total_base = 0
    total_discount = 0
    total_tax = 0
    total_final = 0
    line_items = []

    for item in data.line_items:
        plan = await db.operator_plans.find_one({"id": item.plan_id, "deleted_at": None}, {"_id": 0})
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {item.plan_id} not found")

        tax_amount = 0
        if can_charge_gst and plan.get("tax_percentage", 0) > 0:
            taxable = item.base_amount - item.discount
            if plan.get("tax_type") == "exclusive":
                tax_amount = taxable * (plan["tax_percentage"] / 100)
            elif plan.get("tax_type") == "inclusive":
                tax_amount = taxable - (taxable / (1 + plan["tax_percentage"] / 100))

        final_amount = item.base_amount - item.discount + (tax_amount if plan.get("tax_type") == "exclusive" else 0)

        enriched_item = item.model_dump()
        enriched_item["plan_name"] = plan["name"]
        enriched_item["plan_description"] = plan.get("description")
        enriched_item["tax_amount"] = round(tax_amount, 2)
        enriched_item["final_amount"] = round(final_amount, 2)
        enriched_item["service_start_date"] = item.service_start_date.isoformat()
        enriched_item["service_end_date"] = item.service_end_date.isoformat()
        line_items.append(enriched_item)

        total_base += item.base_amount
        total_discount += item.discount
        total_tax += tax_amount
        total_final += final_amount

    return {
        "subscriber": subscriber,
        "line_items": line_items,
        "base_amount": round(total_base, 2),
        "discount": round(total_discount, 2),
        "tax_amount": round(total_tax, 2),
        "final_amount": round(total_final, 2),
        "due_date": data.due_date.isoformat(),
    }


def _parse_bulk_invoice_date(value: str, field_name: str) -> datetime:
    raw = (value or "").strip()
    if not raw:
        raise ValueError(f"{field_name} is required")

    normalized = raw.replace("T", " ")
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name}. Use YYYY-MM-DD format") from exc


@router.get("/invoices/sample-csv")
async def get_invoices_sample_csv(current_user: dict = Depends(require_operator)):
    """Download a sample CSV template for bulk invoice upload."""
    rows = [
        ["subscriber_whatsapp_number", "plan_name", "base_amount", "discount", "service_start_date", "service_end_date", "due_date"],
        ["9876543210", "Monthly Basic", "599", "0", "2026-03-01", "2026-03-31", "2026-04-05"],
        ["9123456789", "Monthly Basic", "699", "50", "2026-03-01", "2026-03-31", "2026-04-05"],
        ["9988776655", "Fiber Pro", "", "0", "2026-03-15", "2026-04-14", "2026-04-20"],
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices_sample.csv"}
    )


@router.post("/invoices/bulk-upload")
async def bulk_upload_invoices(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_operator)
):
    """Bulk upload invoices from a CSV or XLSX file (background job)."""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot upload invoices")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")

    content = await file.read()
    filename = sanitize_filename(file.filename or "", default="invoices").lower()

    from services.job_queue_service import JobQueueService
    job_id = await JobQueueService.enqueue_job(
        job_type="bulk_upload_invoices",
        operator_id=current_user["operator_id"],
        user_id=current_user["id"],
        payload={
            "filename": filename,
            "file_content": content,
        }
    )

    return {
        "job_id": job_id,
        "message": "Job queued. Poll /api/operator/jobs/{job_id} to check status.",
        "status_url": f"/api/operator/jobs/{job_id}"
    }


def _parse_invoice_document(inv: dict) -> InvoiceResponse:
    inv_data = {**inv}
    inv_data["due_date"] = datetime.fromisoformat(inv["due_date"])
    if inv.get("paid_at"):
        inv_data["paid_at"] = datetime.fromisoformat(inv["paid_at"])
    if inv.get("cancelled_at"):
        inv_data["cancelled_at"] = datetime.fromisoformat(inv["cancelled_at"])
    if "line_items" in inv_data:
        for item in inv_data["line_items"]:
            item["service_start_date"] = datetime.fromisoformat(item["service_start_date"])
            item["service_end_date"] = datetime.fromisoformat(item["service_end_date"])
    return InvoiceResponse(**inv_data)


@router.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(data: InvoiceCreate, request: Request, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot create invoices")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")

    # Block invoice creation if wallet balance is below Rs.50
    from routers.wallet import get_or_create_wallet
    wallet = await get_or_create_wallet(current_user["operator_id"])
    if wallet.get("balance", 0) < 50:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient wallet balance (₹{wallet.get('balance', 0):.2f}). Minimum ₹50 required to generate invoices."
        )

    payload = await _build_invoice_payload(current_user["operator_id"], data)
    subscriber = payload["subscriber"]

    now = datetime.now(timezone.utc)
    invoice = {
        "id": generate_id(),
        "invoice_number": await generate_invoice_number_atomic(db),
        "subscriber_id": data.subscriber_id, "subscriber_name": subscriber["name"],
        "line_items": payload["line_items"],
        "base_amount": payload["base_amount"],
        "discount": payload["discount"],
        "tax_amount": payload["tax_amount"],
        "final_amount": payload["final_amount"],
        "due_date": payload["due_date"], "status": "pending", "payment_id": None,
        "operator_id": current_user["operator_id"],
        "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.invoices.insert_one(invoice)

    # Deduct Rs.10 from operator wallet for invoice generation
    try:
        from routers.wallet import deduct_wallet_for_invoice
        await deduct_wallet_for_invoice(current_user["operator_id"], invoice["id"])
    except Exception as e:
        logger.warning(f"Wallet deduction failed for invoice {invoice['id']}: {e}")

    # Auto-send WhatsApp if whatsapp_notifications addon is active (uses platform WhatsApp config)
    auto_wa_sent = False
    public_invoice_url = build_public_invoice_url(request, invoice)

    if await _has_addon(current_user["operator_id"], "whatsapp_notifications"):
        try:
            wa_config = await _get_platform_whatsapp_config()
            if wa_config:
                template_settings = await _get_whatsapp_template_settings()
                template_name = template_settings.get("invoice_template") or "invoice_notification"
                from services.whatsapp_service import WhatsAppService, build_wa_send_params
                wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
                tmpl_doc = await db.whatsapp_templates.find_one(
                    {"template_name": template_name, "deleted_at": None}, {"_id": 0}
                )
                # Inject invoice_public_url so variable resolver can use it
                invoice["invoice_public_url"] = public_invoice_url or ""

                params = await build_wa_send_params(
                    db, tmpl_doc, invoice, subscriber, invoice_public_url=public_invoice_url
                )

                if params["body_vars"]:
                    await wa_service.send_template_message(
                        recipient_phone=subscriber["whatsapp_number"],
                        template_name=template_name,
                        language_code=params["language_code"],
                        variables=params["variables"],
                        header_params=params["header_params"],
                        header_type=params["header_type"],
                        button_params=params["btn_params"],
                    )
                else:
                    await wa_service.send_invoice_notification(
                        recipient_phone=subscriber["whatsapp_number"],
                        customer_name=subscriber["name"],
                        invoice_number=invoice["invoice_number"],
                        amount=f"₹{invoice['final_amount']:,.2f}",
                        due_date=data.due_date.strftime("%d %b %Y"),
                        payment_link=public_invoice_url,
                        template_name_override=template_name,
                        header_params=params["header_params"],
                        header_type=params["header_type"],
                    )
                auto_wa_sent = True
        except Exception as e:
            logger.warning(f"Auto WhatsApp send failed: {e}")

    # Convert back to InvoiceResponse compatible dict
    response = _parse_invoice_document(invoice)
    result = response.model_dump()
    result["auto_wa_sent"] = auto_wa_sent
    result["has_whatsapp_addon"] = await _has_addon(current_user["operator_id"], "whatsapp_notifications")
    result["public_url"] = public_invoice_url
    result["public_path"] = build_public_invoice_path(invoice)
    return result


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    status: Optional[str] = None, subscriber_id: Optional[str] = None,
    current_user: dict = Depends(require_operator)
):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator invoices")
    query = {"operator_id": current_user["operator_id"], "deleted_at": None}
    if status:
        query["status"] = status
    if subscriber_id:
        query["subscriber_id"] = subscriber_id
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    parsed_invoices = []
    for inv in invoices:
        parsed_invoices.append(_parse_invoice_document(inv))
    
    return parsed_invoices


@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    data: InvoiceUpdate,
    current_user: dict = Depends(require_operator)
):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot edit operator invoices")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")

    invoice = await db.invoices.find_one(
        {"id": invoice_id, "operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending invoices can be edited")

    payload = await _build_invoice_payload(current_user["operator_id"], data)
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "subscriber_id": data.subscriber_id,
        "subscriber_name": payload["subscriber"]["name"],
        "line_items": payload["line_items"],
        "base_amount": payload["base_amount"],
        "discount": payload["discount"],
        "tax_amount": payload["tax_amount"],
        "final_amount": payload["final_amount"],
        "due_date": payload["due_date"],
        "updated_at": now,
    }
    await db.invoices.update_one({"id": invoice_id}, {"$set": updates})
    updated_invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    return _parse_invoice_document(updated_invoice)


@router.put("/invoices/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: str, data: InvoiceStatusUpdate, current_user: dict = Depends(require_operator)
):
    status = sanitize_text(data.status).lower()
    operator_id = current_user.get("operator_id")
    if operator_id and await check_operator_read_only(operator_id):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    if status not in ["pending", "paid", "overdue", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    query = {"id": invoice_id, "deleted_at": None}
    if current_user["role"] != "admin":
        query["operator_id"] = operator_id
    invoice = await db.invoices.find_one(query, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cancelled invoice cannot be changed")
    if invoice["status"] == "paid":
        if status == "cancelled" and current_user["role"] == "admin":
            pass
        elif status != "paid":
            raise HTTPException(status_code=403, detail="Paid invoice cannot be changed by operator")
    if status == "cancelled" and invoice["status"] == "paid" and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can cancel a paid invoice")

    now = datetime.now(timezone.utc)
    updates = {"status": status, "updated_at": now.isoformat()}
    if status == "paid":
        payment_mode = sanitize_text(data.payment_mode or "").lower().replace(" ", "_")
        if payment_mode not in PAYMENT_MODES:
            raise HTTPException(status_code=400, detail="Valid payment mode is required")
        payment_date = data.payment_date or now
        updates["payment_mode"] = payment_mode
        updates["paid_at"] = payment_date.isoformat()
        updates["cancelled_at"] = None
        updates["cancelled_by_role"] = None
    elif status == "cancelled":
        updates["cancelled_at"] = now.isoformat()
        updates["cancelled_by_role"] = current_user["role"]
    else:
        updates["cancelled_at"] = None
        updates["cancelled_by_role"] = None

    await db.invoices.update_one({"id": invoice_id}, {"$set": updates})

    # ── Send WhatsApp payment confirmation ────────────────────────────────────
    if status == "paid":
        try:
            from services.whatsapp_service import get_whatsapp_service_async, build_wa_send_params, log_whatsapp_message
            from services.invoice_view_service import build_public_invoice_url_from_env
            wa_service = await get_whatsapp_service_async()
            if wa_service:
                subscriber = await db.subscribers.find_one(
                    {"id": invoice["subscriber_id"], "deleted_at": None}, {"_id": 0}
                )
                if subscriber and subscriber.get("whatsapp_number"):
                    template_settings = await db.global_settings.find_one(
                        {"type": "whatsapp_template_settings"}, {"_id": 0}
                    ) or {}
                    confirmation_tpl = template_settings.get("payment_confirmation_template") or "payment_confirmation"
                    tmpl_doc = await db.whatsapp_templates.find_one(
                        {"template_name": confirmation_tpl, "deleted_at": None}, {"_id": 0}
                    )
                    inv_public_url = await build_public_invoice_url_from_env(invoice)
                    params = await build_wa_send_params(db, tmpl_doc, invoice, subscriber, invoice_public_url=inv_public_url)

                    wa_result = None
                    if params["body_vars"]:
                        wa_result = await wa_service.send_template_message(
                            recipient_phone=subscriber["whatsapp_number"],
                            template_name=confirmation_tpl,
                            language_code=params["language_code"],
                            variables=params["variables"],
                            header_params=params["header_params"],
                            header_type=params["header_type"],
                            button_params=params["btn_params"],
                        )
                    else:
                        paid_at = updates.get("paid_at", now.isoformat())
                        payment_date_str = paid_at[:10] if paid_at else now.strftime("%Y-%m-%d")
                        wa_result = await wa_service.send_payment_confirmation(
                            recipient_phone=subscriber["whatsapp_number"],
                            customer_name=subscriber["name"],
                            invoice_number=invoice["invoice_number"],
                            amount_paid=f"INR {invoice['final_amount']:,.2f}",
                            payment_date=payment_date_str,
                        )

                    # Log the send
                    wa_msg_id = (wa_result.get("messages") or [{}])[0].get("id", "") if wa_result else ""
                    wa_wa_id = (wa_result.get("contacts") or [{}])[0].get("wa_id", "") if wa_result else ""
                    await log_whatsapp_message(
                        db,
                        operator_id=operator_id,
                        template_name=confirmation_tpl,
                        template_category="payment_confirmation",
                        recipient_phone=subscriber["whatsapp_number"],
                        status="sent",
                        message_id=wa_msg_id,
                        wa_id=wa_wa_id,
                        invoice_id=invoice["id"],
                        invoice_number=invoice["invoice_number"],
                        trigger="payment_confirmation",
                    )
        except Exception as wa_err:
            logger.warning(f"WhatsApp payment confirmation failed for invoice {invoice_id}: {wa_err}")

    return {"message": f"Invoice marked as {status}"}


@router.post("/invoices/{invoice_id}/payment-link", response_model=PaymentLinkResponse)
async def create_payment_link(invoice_id: str, current_user: dict = Depends(require_operator)):
    from services.razorpay_service import RazorpayService
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Determine which payment gateway to use:
    # - payment_gateway addon with operator's own configured keys → operator's own keys
    # - payment_gateway addon without own keys → platform keys
    if not await _has_addon(current_user["operator_id"], "payment_gateway"):
        raise HTTPException(status_code=403, detail="Payment gateway add-on is not enabled. Please activate the 'Payment Gateway' add-on.")

    operator_gateway = await db.payment_gateways.find_one({"operator_id": current_user["operator_id"], "is_active": True}, {"_id": 0})
    if operator_gateway:
        # Use operator's own gateway keys
        gateway = operator_gateway
    else:
        # Use platform gateway keys
        gateway = await db.payment_gateways.find_one({"is_platform_gateway": True, "is_active": True}, {"_id": 0})
        if not gateway:
            raise HTTPException(status_code=400, detail="Platform payment gateway not configured. Please contact admin.")

    subscriber = await db.subscribers.find_one({"id": invoice["subscriber_id"], "deleted_at": None}, {"_id": 0})
    try:
        razorpay_service = RazorpayService(gateway["api_key"], gateway["api_secret"])
        payment_link = razorpay_service.create_payment_link(
            amount=invoice["final_amount"],
            description=f"Invoice {invoice['invoice_number']}",
            customer_name=subscriber["name"] if subscriber else "",
            customer_email=subscriber.get("email", "") if subscriber else "",
            customer_phone=subscriber.get("whatsapp_number", "") if subscriber else "",
            invoice_number=invoice["invoice_number"]
        )
        qr_code = razorpay_service.generate_qr_code(payment_link["short_url"])
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {"payment_link": payment_link["short_url"], "payment_link_id": payment_link["id"],
                      "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return PaymentLinkResponse(
            payment_link=payment_link["short_url"], payment_link_id=payment_link["id"],
            qr_code=qr_code, amount=invoice["final_amount"]
        )
    except Exception as e:
        logger.error(f"Payment link creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create payment link: {e}")


@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: str, current_user: dict = Depends(require_operator)):
    from services.pdf_service import InvoicePDFService
    from services.razorpay_service import RazorpayService
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    subscriber = await db.subscribers.find_one({"id": invoice["subscriber_id"], "deleted_at": None}, {"_id": 0})
    plan = await db.operator_plans.find_one({"id": invoice["plan_id"], "deleted_at": None}, {"_id": 0})
    qr_code = None
    if invoice.get("payment_link"):
        gateway = await db.payment_gateways.find_one({"operator_id": current_user["operator_id"]}, {"_id": 0})
        if gateway:
            try:
                razorpay_service = RazorpayService(gateway["api_key"], gateway["api_secret"])
                qr_code = razorpay_service.generate_qr_code(invoice["payment_link"])
            except Exception:
                pass
    pdf_service = InvoicePDFService()
    inv_settings = await db.invoice_settings.find_one(
        {"operator_id": current_user["operator_id"]}, {"_id": 0}
    )
    invoice_settings = normalize_invoice_settings(inv_settings, operator)
    template = invoice_settings.get("invoice_template", "classic")
    pdf_bytes = pdf_service.generate_invoice_pdf(
        invoice_data=invoice, operator_data={**(operator or {}), **invoice_settings},
        subscriber_data=subscriber or {}, plan_data=plan or {}, qr_code_base64=qr_code,
        template=template,
    )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Invoice_{invoice['invoice_number']}.pdf"}
    )


# ─── Staff ────────────────────────────────────────────────────────────────────

@router.post("/staff", response_model=StaffResponse)
async def create_staff(data: StaffCreate, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot create staff")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if operator:
        # Block staff creation on trial plan with a clear message
        if operator.get("status") == "trial":
            raise HTTPException(status_code=403, detail="Please subscribe to use this feature.")
        # Use operator-level max_staff override (set when staff_management addon is assigned)
        # falling back to the SaaS plan's max_staff
        operator_max_staff = operator.get("max_staff")
        if operator_max_staff is None:
            plan = await db.saas_plans.find_one({"id": operator.get("saas_plan_id"), "deleted_at": None}, {"_id": 0})
            operator_max_staff = plan["max_staff"] if plan else 0
        current_count = await db.users.count_documents(
            {"operator_id": current_user["operator_id"], "role": "staff", "deleted_at": None}
        )
        if current_count >= operator_max_staff:
            raise HTTPException(status_code=403, detail=f"Staff limit ({operator_max_staff}) reached")
    existing = await db.users.find_one({"email": data.email, "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    now = datetime.now(timezone.utc)
    user_id = generate_id()
    user = {
        "id": user_id, "email": data.email, "name": data.name, "phone": data.phone,
        "password": hash_password(data.password), "role": "staff",
        "permissions": data.permissions, "operator_id": current_user["operator_id"],
        "status": "active", "created_at": now.isoformat(),
        "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.users.insert_one(user)
    return StaffResponse(
        id=user_id, name=data.name, email=data.email, phone=data.phone,
        role="staff", permissions=data.permissions,
        operator_id=current_user["operator_id"], status="active", created_at=now
    )


@router.put("/staff/{staff_id}", response_model=StaffResponse)
async def update_staff(staff_id: str, data: StaffUpdate, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot update staff")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")

    existing = await db.users.find_one({
        "id": staff_id, 
        "operator_id": current_user["operator_id"], 
        "role": "staff", 
        "deleted_at": None
    })
    if not existing:
        raise HTTPException(status_code=404, detail="Staff not found")

    if data.email and data.email != existing.get("email"):
        email_check = await db.users.find_one({"email": data.email, "deleted_at": None})
        if email_check:
            raise HTTPException(status_code=400, detail="Email already registered")

    update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
    dump_data = data.model_dump(exclude_unset=True)
    
    for key, value in dump_data.items():
        if key == "password":
            if value:
                update_doc[key] = hash_password(value)
        else:
            update_doc[key] = value

    await db.users.update_one({"id": staff_id}, {"$set": update_doc})
    
    updated = await db.users.find_one({"id": staff_id})
    return StaffResponse(
        id=updated["id"],
        name=updated["name"],
        email=updated["email"],
        phone=updated.get("phone"),
        role=updated["role"],
        permissions=updated.get("permissions", []),
        operator_id=updated["operator_id"],
        status=updated.get("status", "active"),
        created_at=datetime.fromisoformat(updated["created_at"])
    )


@router.get("/staff", response_model=List[StaffResponse])
async def get_staff(current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator staff")
    staff = await db.users.find(
        {"operator_id": current_user["operator_id"], "role": "staff", "deleted_at": None},
        {"_id": 0, "password": 0}
    ).to_list(100)
    return [StaffResponse(**{**s, "permissions": s.get("permissions", []),
                             "created_at": datetime.fromisoformat(s["created_at"])}) for s in staff]


@router.delete("/staff/{staff_id}")
async def delete_staff(staff_id: str, current_user: dict = Depends(require_operator_no_staff)):
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    result = await db.users.update_one(
        {"id": staff_id, "operator_id": current_user["operator_id"], "role": "staff", "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"message": "Staff deleted"}


# ─── Payment Gateway ────────────────────────────────────────────────────────

@router.post("/payment-gateway")
async def configure_payment_gateway(data: PaymentGatewayConfig, current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot configure operator payment gateway")
    raise HTTPException(status_code=403, detail="Payment gateway keys are managed by admin. Please contact admin for updates.")
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    if not await _has_addon(current_user["operator_id"], "payment_gateway"):
        raise HTTPException(status_code=403, detail="Payment Gateway add-on is not enabled for your plan.")
    now = datetime.now(timezone.utc)
    gateway_config = {
        "id": generate_id(), "operator_id": current_user["operator_id"],
        "gateway_type": data.gateway_type, "api_key": data.api_key,
        "api_secret": data.api_secret, "webhook_secret": data.webhook_secret,
        "is_active": True, "created_at": now.isoformat(), "updated_at": now.isoformat()
    }
    await db.payment_gateways.update_one(
        {"operator_id": current_user["operator_id"]}, {"$set": gateway_config}, upsert=True
    )
    return {"message": "Payment gateway configured successfully"}


@router.get("/payment-gateway")
async def get_payment_gateway(current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator payment gateway")
    gateway = await db.payment_gateways.find_one(
        {"operator_id": current_user["operator_id"]}, {"_id": 0, "api_secret": 0}
    )
    if not gateway:
        return {"configured": False}
    return {
        "configured": True, "gateway_type": gateway["gateway_type"],
        "api_key": gateway["api_key"][:8] + "****", "is_active": gateway.get("is_active", False)
    }


# ─── Reports ─────────────────────────────────────────────────────────────────

@router.get("/reports/revenue")
async def get_revenue_report(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    current_user: dict = Depends(require_operator)
):
    start_date = sanitize_text(start_date) if start_date else start_date
    end_date = sanitize_text(end_date) if end_date else end_date
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator reports")
    query = {"operator_id": current_user["operator_id"], "status": "paid", "deleted_at": None}
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        query.setdefault("created_at", {})["$lte"] = end_date
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(10000)
    return {
        "total_invoices": len(invoices),
        "total_revenue": round(sum(inv.get("final_amount", 0) for inv in invoices), 2),
        "total_base_amount": round(sum(inv.get("base_amount", 0) for inv in invoices), 2),
        "total_tax": round(sum(inv.get("tax_amount", 0) for inv in invoices), 2),
        "total_discount": round(sum(inv.get("discount", 0) for inv in invoices), 2),
    }


@router.get("/reports/gst-summary")
async def get_gst_summary(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    current_user: dict = Depends(require_operator)
):
    start_date = sanitize_text(start_date) if start_date else start_date
    end_date = sanitize_text(end_date) if end_date else end_date
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator reports")
    query = {"operator_id": current_user["operator_id"], "deleted_at": None}
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        query.setdefault("created_at", {})["$lte"] = end_date
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(10000)
    total_taxable = sum(inv.get("base_amount", 0) - inv.get("discount", 0) for inv in invoices)
    total_gst = sum(inv.get("tax_amount", 0) for inv in invoices)
    return {
        "total_taxable_amount": round(total_taxable, 2), "total_gst_collected": round(total_gst, 2),
        "cgst": round(total_gst / 2, 2), "sgst": round(total_gst / 2, 2)
    }


@router.get("/reports/pending-overdue")
async def get_pending_overdue_report(current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator reports")
    pending = await db.invoices.find(
        {"operator_id": current_user["operator_id"], "status": "pending", "deleted_at": None}, {"_id": 0}
    ).to_list(1000)
    overdue = await db.invoices.find(
        {"operator_id": current_user["operator_id"], "status": "overdue", "deleted_at": None}, {"_id": 0}
    ).to_list(1000)
    return {
        "pending_count": len(pending), "pending_amount": round(sum(inv.get("final_amount", 0) for inv in pending), 2),
        "overdue_count": len(overdue), "overdue_amount": round(sum(inv.get("final_amount", 0) for inv in overdue), 2)
    }


@router.get("/reports/invoices")
async def get_report_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    current_user: dict = Depends(require_operator),
):
    """Get paginated invoice list with filters for reports."""
    status = sanitize_text(status) if status else status
    search = sanitize_text(search) if search else search
    start_date = sanitize_text(start_date) if start_date else start_date
    end_date = sanitize_text(end_date) if end_date else end_date
    sort_by = sanitize_text(sort_by) if sort_by else sort_by
    sort_order = sanitize_text(sort_order) if sort_order else sort_order
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator reports")
    query = {"operator_id": current_user["operator_id"], "deleted_at": None}

    # Status filter
    if status and status != "all":
        query["status"] = status

    # Date range filter on created_at
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date + "T23:59:59"
        query["created_at"] = date_filter

    # Text search on invoice_number or subscriber_name
    if search and search.strip():
        search_regex = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"invoice_number": search_regex},
            {"subscriber_name": search_regex},
        ]

    # Sort
    sort_dir = -1 if sort_order == "desc" else 1
    valid_sort_fields = {"created_at", "final_amount", "due_date", "invoice_number", "status"}
    sort_field = sort_by if sort_by in valid_sort_fields else "created_at"

    # Count total
    total = await db.invoices.count_documents(query)

    # Paginate
    skip = (page - 1) * limit
    invoices = await db.invoices.find(query, {"_id": 0}).sort(
        sort_field, sort_dir
    ).skip(skip).limit(limit).to_list(limit)

    return {
        "invoices": invoices,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": max(1, -(-total // limit)),  # ceil division
    }


# ─── Audit Logs ────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_operator_audit_logs(
    skip: int = 0, limit: int = 50, current_user: dict = Depends(require_operator)
):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Use admin audit logs endpoint")
    if not await _has_addon(current_user["operator_id"], "audit_log"):
        raise HTTPException(status_code=403, detail="Audit Logs add-on is not enabled for your plan.")
    logs = await db.audit_logs.find(
        {"operator_id": current_user["operator_id"]}, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [AuditLogResponse(**{**log, "created_at": datetime.fromisoformat(log["created_at"])}) for log in logs]



# ─── WhatsApp Notifications (uses platform global WhatsApp config) ────────────

@router.post("/send-notification")
async def send_whatsapp_notification(data: SendNotificationRequest, request: Request, current_user: dict = Depends(require_operator)):
    from services.whatsapp_service import WhatsAppService, resolve_template_variables
    from services.invoice_view_service import build_public_invoice_url
    
    # Check wallet balance before sending (Rs 0.5 per message)
    WHATSAPP_SEND_COST = 0.5
    wallet = await get_or_create_wallet(current_user["operator_id"])
    current_balance = wallet.get("balance", 0)
    
    if current_balance < WHATSAPP_SEND_COST:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail=f"Insufficient wallet balance. Required: ₹{WHATSAPP_SEND_COST}, Available: ₹{current_balance:.2f}. Please top up your wallet."
        )
    
    wa_config = await _get_platform_whatsapp_config()
    if not wa_config:
        raise HTTPException(status_code=400, detail="WhatsApp not configured. Please contact admin.")
    invoice = await db.invoices.find_one(
        {"id": data.invoice_id, "operator_id": current_user["operator_id"], "deleted_at": None}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    subscriber = await db.subscribers.find_one({"id": invoice["subscriber_id"], "deleted_at": None}, {"_id": 0})
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    if not subscriber.get("whatsapp_number"):
        raise HTTPException(status_code=400, detail="Subscriber has no WhatsApp number configured.")

    # Build public invoice URL from request origin
    invoice_public_url = build_public_invoice_url(request, invoice) or ""
    # Inject into invoice dict so variable resolver can access it
    invoice["invoice_public_url"] = invoice_public_url

    try:
        template_settings = await _get_whatsapp_template_settings()
        wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
        result = None

        def _get_header_and_btn(tmpl_doc, body_vars):
            """Return (header_params, header_type, btn_params) based on template config."""
            hdr_type = (tmpl_doc or {}).get("header_type", "none")
            # For image headers: use the fixed URL stored in template (header_image_url)
            # This is set by admin; it's the actual image URL sent in every message.
            hdr_params = None
            if hdr_type == "image":
                fixed_url = (tmpl_doc or {}).get("header_image_url", "") or ""
                if fixed_url:
                    hdr_params = [fixed_url]
                # if no fixed URL, will be resolved from header_variable later

            # Button URL
            btn_url_var = (tmpl_doc or {}).get("button_url_variable", "invoice_public_url")
            if btn_url_var == "invoice_number":
                btn_url = invoice.get("invoice_number", "")
            else:
                btn_url = invoice_public_url

            btn_params = None
            if (tmpl_doc or {}).get("has_payment_button") and btn_url:
                btn_params = [{"sub_type": "url", "parameters": [{"type": "text", "text": btn_url}]}]

            return hdr_params, hdr_type, btn_params

        if data.notification_type == "reminder":
            template_name = template_settings.get("reminder_template") or "payment_reminder"
            tmpl_doc = await db.whatsapp_templates.find_one(
                {"template_name": template_name, "deleted_at": None}, {"_id": 0}
            )
            body_vars = (tmpl_doc or {}).get("body_variables") or []
            hdr_params, hdr_type, btn_params = _get_header_and_btn(tmpl_doc, body_vars)

            # If image header but no fixed URL, try resolving from header_variable
            if hdr_type == "image" and not hdr_params and (tmpl_doc or {}).get("header_variable"):
                res_hdr = await resolve_template_variables(
                    db, [], invoice, subscriber,
                    header_variable=(tmpl_doc or {}).get("header_variable")
                )
                hdr_params = [res_hdr["header"]] if res_hdr.get("header") else None

            res = await resolve_template_variables(db, body_vars, invoice, subscriber)
            variables = res["body"]

            if body_vars:
                result = await wa_service.send_template_message(
                    recipient_phone=subscriber["whatsapp_number"],
                    template_name=template_name,
                    language_code=(tmpl_doc or {}).get("language_code", "en"),
                    variables=variables,
                    header_params=hdr_params,
                    header_type=hdr_type,
                    button_params=btn_params,
                )
            else:
                due_date = datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00'))
                days_overdue = max(0, (datetime.now(timezone.utc) - due_date).days)
                result = await wa_service.send_payment_reminder(
                    recipient_phone=subscriber["whatsapp_number"],
                    customer_name=subscriber["name"],
                    invoice_number=invoice["invoice_number"],
                    amount_due=f"₹{invoice['final_amount']:,.2f}",
                    days_overdue=str(days_overdue),
                    payment_link=invoice_public_url or invoice.get("payment_link"),
                    template_name_override=template_name,
                    header_params=hdr_params,
                    header_type=hdr_type,
                )
        else:
            template_name = template_settings.get("invoice_template") or "invoice_notification"
            tmpl_doc = await db.whatsapp_templates.find_one(
                {"template_name": template_name, "deleted_at": None}, {"_id": 0}
            )
            body_vars = (tmpl_doc or {}).get("body_variables") or []
            hdr_params, hdr_type, btn_params = _get_header_and_btn(tmpl_doc, body_vars)

            # If image header but no fixed URL, try resolving from header_variable
            if hdr_type == "image" and not hdr_params and (tmpl_doc or {}).get("header_variable"):
                res_hdr = await resolve_template_variables(
                    db, [], invoice, subscriber,
                    header_variable=(tmpl_doc or {}).get("header_variable")
                )
                hdr_params = [res_hdr["header"]] if res_hdr.get("header") else None

            res = await resolve_template_variables(db, body_vars, invoice, subscriber)
            variables = res["body"]

            if body_vars:
                result = await wa_service.send_template_message(
                    recipient_phone=subscriber["whatsapp_number"],
                    template_name=template_name,
                    language_code=(tmpl_doc or {}).get("language_code", "en"),
                    variables=variables,
                    header_params=hdr_params,
                    header_type=hdr_type,
                    button_params=btn_params,
                )
            else:
                result = await wa_service.send_invoice_notification(
                    recipient_phone=subscriber["whatsapp_number"],
                    customer_name=subscriber["name"],
                    invoice_number=invoice["invoice_number"],
                    amount=f"₹{invoice['final_amount']:,.2f}",
                    due_date=datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00')).strftime("%d %b %Y"),
                    payment_link=invoice_public_url or invoice.get("payment_link"),
                    template_name_override=template_name,
                    header_params=hdr_params,
                    header_type=hdr_type,
                )

        msg_id = None
        recipient_wa_id = None
        if result and "messages" in result and len(result["messages"]) > 0:
            msg_id = result["messages"][0].get("id")
        if result and "contacts" in result and len(result["contacts"]) > 0:
            recipient_wa_id = result["contacts"][0].get("wa_id")
        
        # Log the message send
        try:
            from services.whatsapp_service import log_whatsapp_message
            await log_whatsapp_message(
                db,
                operator_id=current_user["operator_id"],
                template_name=template_name,
                template_category=data.notification_type,
                recipient_phone=subscriber["whatsapp_number"],
                status="sent",
                message_id=msg_id or "",
                wa_id=recipient_wa_id or "",
                invoice_id=invoice["id"],
                invoice_number=invoice["invoice_number"],
                trigger="manual",
            )
        except Exception as log_e:
            logger.warning(f"WhatsApp message log failed: {log_e}")

        # Deduct wallet balance after successful send
        new_balance, became_suspended = await deduct_wallet(
            current_user["operator_id"],
            WHATSAPP_SEND_COST,
            f"WhatsApp message sent to {subscriber['name']} (Invoice: {invoice['invoice_number']})",
            reference_id=invoice["id"]
        )
        logger.info(f"Wallet deducted ₹{WHATSAPP_SEND_COST} for WhatsApp send. New balance: ₹{new_balance}")
        
        return {
            "success": True,
            "message_id": msg_id,
            "recipient_wa_id": recipient_wa_id,
            "detail": f"Message sent to {recipient_wa_id or subscriber.get('whatsapp_number', '')}",
            "wallet_balance": new_balance,
        }
    except Exception as e:
        logger.error(f"WhatsApp notification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {e}")


@router.post("/bulk-notification")
async def send_bulk_notification(data: BulkNotificationRequest, current_user: dict = Depends(require_operator)):
    """Send bulk WhatsApp notifications (background job)."""
    from services.job_queue_service import JobQueueService

    job_id = await JobQueueService.enqueue_job(
        job_type="bulk_notification",
        operator_id=current_user["operator_id"],
        user_id=current_user["id"],
        payload={
            "subscriber_ids": data.subscriber_ids,
            "message_template": getattr(data, "message_template", "invoice_notification"),
        }
    )

    return {
        "job_id": job_id,
        "message": "Notification job queued. Poll /api/operator/jobs/{job_id} to check status.",
        "status_url": f"/api/operator/jobs/{job_id}"
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, current_user: dict = Depends(require_operator)):
    """Get status of a background job."""
    from services.job_queue_service import JobQueueService
    from models import BackgroundJobResponse

    job = await JobQueueService.get_job(job_id, current_user["operator_id"])
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return BackgroundJobResponse(**job)


# ─── Reminder Settings (moved to global admin) ──────────────────────────────
# GET /reminder-settings and PUT /reminder-settings are now admin-only endpoints
# located in admin.py. Operators are subject to the platform-wide reminder config.


# ─── WhatsApp WebJS Integration ──────────────────────────────────────────────
# These endpoints proxy requests to the WhatsApp WebJS microservice for operators
# to connect their personal WhatsApp accounts via QR code scanning.

import httpx
from config import WHATSAPP_WEBJS_URL

@router.post("/whatsapp-webjs/init")
async def init_whatsapp_webjs(current_user: dict = Depends(require_operator)):
    """Initialize WhatsApp WebJS client for the operator."""
    operator_id = current_user["operator_id"]
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{WHATSAPP_WEBJS_URL}/init/{operator_id}")
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WhatsApp WebJS service is not available")
    except Exception as e:
        logger.error(f"WhatsApp WebJS init error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whatsapp-webjs/status")
async def get_whatsapp_webjs_status(current_user: dict = Depends(require_operator)):
    """Get WhatsApp WebJS connection status for the operator."""
    operator_id = current_user["operator_id"]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{WHATSAPP_WEBJS_URL}/status/{operator_id}")
            return response.json()
    except httpx.ConnectError:
        return {"status": "service_unavailable", "hasQR": False}
    except Exception as e:
        logger.error(f"WhatsApp WebJS status error: {e}")
        return {"status": "error", "hasQR": False, "error": str(e)}


@router.get("/whatsapp-webjs/qr")
async def get_whatsapp_webjs_qr(current_user: dict = Depends(require_operator)):
    """Get QR code for WhatsApp WebJS authentication."""
    operator_id = current_user["operator_id"]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{WHATSAPP_WEBJS_URL}/qr/{operator_id}")
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WhatsApp WebJS service is not available")
    except Exception as e:
        logger.error(f"WhatsApp WebJS QR error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whatsapp-webjs/disconnect")
async def disconnect_whatsapp_webjs(current_user: dict = Depends(require_operator)):
    """Disconnect WhatsApp WebJS client for the operator."""
    operator_id = current_user["operator_id"]
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{WHATSAPP_WEBJS_URL}/disconnect/{operator_id}")
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WhatsApp WebJS service is not available")
    except Exception as e:
        logger.error(f"WhatsApp WebJS disconnect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from pydantic import BaseModel

class WhatsAppWebJSSendRequest(BaseModel):
    phone: str
    message: str

@router.post("/whatsapp-webjs/send")
async def send_whatsapp_webjs_message(
    data: WhatsAppWebJSSendRequest,
    current_user: dict = Depends(require_operator)
):
    """Send a message via WhatsApp WebJS."""
    operator_id = current_user["operator_id"]
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{WHATSAPP_WEBJS_URL}/send/{operator_id}",
                json={"phone": data.phone, "message": data.message}
            )
            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data.get("error", "Failed to send message"))
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WhatsApp WebJS service is not available. Please try again later.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WhatsApp WebJS send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whatsapp-webjs/send-invoice/{invoice_id}")
async def send_invoice_via_webjs(
    invoice_id: str,
    current_user: dict = Depends(require_operator)
):
    """Send invoice details via WhatsApp WebJS."""
    operator_id = current_user["operator_id"]
    
    # Get invoice details
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "operator_id": operator_id, "deleted_at": None}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get subscriber details
    subscriber = await db.subscribers.find_one(
        {"id": invoice["subscriber_id"], "deleted_at": None}, {"_id": 0}
    )
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    whatsapp_number = subscriber.get("whatsapp_number")
    if not whatsapp_number:
        raise HTTPException(status_code=400, detail="Subscriber does not have a WhatsApp number")
    
    # Get operator details for company name
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    company_name = operator.get("company_name", "Your Service Provider") if operator else "Your Service Provider"
    
    # Build invoice message
    due_date = datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00')).strftime("%d %b %Y")
    amount = f"₹{invoice['final_amount']:,.2f}"
    
    message = f"""*Invoice from {company_name}*

Invoice No: {invoice['invoice_number']}
Amount Due: {amount}
Due Date: {due_date}

Dear {subscriber['name']},

This is a reminder for your pending invoice. Please make the payment at your earliest convenience."""

    # Add payment link if available
    if invoice.get("payment_link"):
        message += f"\n\nPay online: {invoice['payment_link']}"
    
    message += "\n\nThank you for your business!"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First check if WhatsApp is connected
            status_response = await client.get(f"{WHATSAPP_WEBJS_URL}/status/{operator_id}")
            status_data = status_response.json()
            
            if status_data.get("status") != "ready":
                raise HTTPException(
                    status_code=400, 
                    detail="WhatsApp is not connected. Please connect your WhatsApp from Settings first."
                )
            
            # Send the message
            response = await client.post(
                f"{WHATSAPP_WEBJS_URL}/send/{operator_id}",
                json={"phone": whatsapp_number, "message": message}
            )
            
            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(status_code=response.status_code, detail=error_data.get("error", "Failed to send message"))
            
            result = response.json()
            
            # Log the action
            await log_audit(
                operator_id=operator_id,
                action="whatsapp_webjs_invoice_sent",
                entity_type="invoice",
                entity_id=invoice_id,
                details={
                    "invoice_number": invoice["invoice_number"],
                    "subscriber_name": subscriber["name"],
                    "phone": whatsapp_number
                },
                user_id=current_user.get("user_id") or current_user.get("id"),
                user_name=current_user.get("name", "System")
            )
            
            return {"success": True, "message_id": result.get("messageId")}
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WhatsApp WebJS service is not available. Please try again later.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WhatsApp WebJS send invoice error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
