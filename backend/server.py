"""
Multi-Tenant SaaS Billing Platform — FastAPI entry point.

Modules:
  database.py       — MongoDB connection (db)
  config.py         — JWT & other constants
  models.py         — All Pydantic schemas
  utils.py          — ID generation, password hashing, JWT helpers
  dependencies.py   — FastAPI dependency functions (auth guards)
  audit.py          — Audit-log helper
  routers/
    auth.py         — /api/auth/*
    admin.py        — /api/admin/*
    operator.py     — /api/operator/*
    webhooks.py     — /api/webhooks/*
  services/
    razorpay_service.py
    whatsapp_service.py
    pdf_service.py
    cron_service.py
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import traceback

from database import db, close_db
from routers.auth import router as auth_router
from routers.admin import router as admin_router
from routers.operator import router as operator_router
from routers.webhooks import router as webhooks_router
from routers.backup import router as backup_router, _do_backup
from routers.public import router as public_router

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── App & routers ───────────────────────────────────────────────────────────
app = FastAPI(title="Multi-Tenant SaaS Billing Platform")

app.include_router(auth_router,      prefix="/api")
app.include_router(admin_router,     prefix="/api")
app.include_router(operator_router,  prefix="/api")
app.include_router(webhooks_router,  prefix="/api")
app.include_router(backup_router,    prefix="/api")
app.include_router(public_router,    prefix="/api")

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error Logging Middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def error_logging_middleware(request: Request, call_next):
    """Capture and log all 4xx/5xx errors to error_logs collection."""
    try:
        response = await call_next(request)
        # Log server errors (5xx) from middleware
        if response.status_code >= 500:
            from error_logger import log_error
            await log_error(
                error_type="server_error",
                message=f"Server error {response.status_code} on {request.method} {request.url.path}",
                module="middleware",
                endpoint=request.url.path,
                request_method=request.method,
                request_path=str(request.url.path),
                status_code=response.status_code,
                ip_address=request.client.host if request.client else "",
            )
        return response
    except Exception as exc:
        from error_logger import log_error
        await log_error(
            error_type="unhandled_exception",
            message=str(exc),
            module="middleware",
            endpoint=request.url.path,
            request_method=request.method,
            request_path=str(request.url.path),
            status_code=500,
            stack_trace=traceback.format_exc(),
            ip_address=request.client.host if request.client else "",
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Misc endpoints ──────────────────────────────────────────────────────────

# Log explicit HTTPExceptions (4xx client errors) for visibility
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException as FastAPIHTTPException


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    """Log 4xx and 5xx HTTPExceptions to error_logs."""
    # Skip 401 unauthorized (auth failures are normal) and OPTIONS preflight
    if exc.status_code >= 400 and exc.status_code != 401 and request.method != "OPTIONS":
        try:
            from error_logger import log_error
            severity = "client_error" if exc.status_code < 500 else "server_error"
            await log_error(
                error_type=severity,
                message=str(exc.detail),
                module="http_exception",
                endpoint=request.url.path,
                request_method=request.method,
                request_path=str(request.url.path),
                status_code=exc.status_code,
                ip_address=request.client.host if request.client else "",
            )
        except Exception:
            pass
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors."""
    try:
        from error_logger import log_error
        await log_error(
            error_type="validation_error",
            message=str(exc.errors()),
            module="request_validation",
            endpoint=request.url.path,
            request_method=request.method,
            request_path=str(request.url.path),
            status_code=422,
            ip_address=request.client.host if request.client else "",
        )
    except Exception:
        pass
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "E-Bill - ISP & Cable Billing Solutions"}


@app.get("/api/landing-page")
async def get_landing_page_public():
    """Public endpoint for landing page settings (no auth required)."""
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
    settings = await db.global_settings.find_one({"type": "landing_page"}, {"_id": 0})
    if not settings:
        return DEFAULT_LANDING_PAGE_SETTINGS
    return settings.get("settings", DEFAULT_LANDING_PAGE_SETTINGS)


@app.post("/api/seed")
async def seed_data():
    """Seed initial admin, addons, and default SaaS plans (idempotent)."""
    from utils import generate_id, hash_password
    from datetime import datetime, timezone

    seeded = []
    now = datetime.now(timezone.utc)

    # Admin user
    if not await db.users.find_one({"role": "admin", "deleted_at": None}):
        admin_user = {
            "id": generate_id(), "email": "admin@saas.com", "name": "Super Admin",
            "phone": "9999999999", "password": hash_password("admin123"),
            "role": "admin", "operator_id": None, "status": "active",
            "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None
        }
        await db.users.insert_one(admin_user)
        seeded.append("admin_user")

    # Required addons
    required_addons = [
        {"code": "audit_log",              "name": "Audit Logs",               "price": 100, "description": "Full audit trail of all user actions"},
        {"code": "payment_gateway",        "name": "Payment Gateway",          "price": 100, "description": "Collect online payments from subscribers"},
        {"code": "custom_payment_gateway", "name": "Custom Payment Gateway",   "price": 100, "description": "Use your own Razorpay/Cashfree credentials"},
        {"code": "announcement",           "name": "Announcements",            "price": 100, "description": "Send bulk announcements (max 3/day)"},
        {"code": "whatsapp_notifications", "name": "WhatsApp Notifications",   "price": 100, "description": "Send WhatsApp invoices, reminders and notifications to subscribers"},
        {"code": "staff_management",       "name": "Staff Management",         "price": 100, "description": "Allow up to 5 staff members for your account"},
    ]
    for addon_data in required_addons:
        existing = await db.addons.find_one({"code": addon_data["code"], "deleted_at": None})
        if not existing:
            await db.addons.insert_one({
                "id": generate_id(), **addon_data,
                "status": "active", "created_at": now.isoformat(), "deleted_at": None
            })
            seeded.append(f"addon:{addon_data['code']}")

    # SaaS Plans — only seed if none exist
    if not await db.saas_plans.find_one({"deleted_at": None}):
        plans = [
            {"id": generate_id(), "name": "Basic", "monthly_price": 500,
             "max_subscribers": 200, "max_staff": 0, "trial_enabled": False, "trial_days": 0,
             "gst_applicable": True, "included_addons": [],
             "platform_fee_percentage": 3.5,
             "status": "active", "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None},
            {"id": generate_id(), "name": "Pro", "monthly_price": 2500,
             "max_subscribers": 1000, "max_staff": 5, "trial_enabled": False, "trial_days": 0,
             "gst_applicable": True, "included_addons": [],
             "platform_fee_percentage": 3.0,
             "status": "active", "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None},
        ]
        await db.saas_plans.insert_many(plans)
        seeded.append("saas_plans")

    # Migrate: replace payment_reminder with whatsapp_notifications in all existing data
    # Update SaaS plans
    await db.saas_plans.update_many(
        {"included_addons": "payment_reminder"},
        {"$addToSet": {"included_addons": "whatsapp_notifications"}}
    )
    await db.saas_plans.update_many(
        {"included_addons": "payment_reminder"},
        {"$pull": {"included_addons": "payment_reminder"}}
    )
    # Update operators
    await db.operators.update_many(
        {"active_addons": "payment_reminder"},
        {"$addToSet": {"active_addons": "whatsapp_notifications"}}
    )
    await db.operators.update_many(
        {"active_addons": "payment_reminder"},
        {"$pull": {"active_addons": "payment_reminder"}}
    )

    if not seeded:
        return {"message": "Data already seeded (migration applied)"}

    return {
        "message": "Data seeded successfully",
        "seeded": seeded,
        "admin_email": "admin@saas.com",
        "admin_password": "admin123"
    }


# ── Shutdown ────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Start scheduled jobs: daily backup, invoice generation, reminders, expiry check."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from services.cron_service import (
        run_daily_invoice_generation,
        run_daily_reminder_processing,
        run_daily_expiry_check,
        run_daily_settlement_processing,
    )

    scheduler = AsyncIOScheduler()

    # Daily auto-backup at 02:00 UTC
    scheduler.add_job(
        lambda: __import__("asyncio").get_event_loop().create_task(_do_backup("auto")),
        "cron", hour=2, minute=0, id="daily_backup"
    )

    # Daily auto-invoice generation at 06:00 UTC
    scheduler.add_job(
        lambda: __import__("asyncio").get_event_loop().create_task(run_daily_invoice_generation(db)),
        "cron", hour=6, minute=0, id="daily_invoices"
    )

    # Daily scheduled reminder processing at 07:00 UTC
    scheduler.add_job(
        lambda: __import__("asyncio").get_event_loop().create_task(run_daily_reminder_processing(db)),
        "cron", hour=7, minute=0, id="daily_reminders"
    )

    # Daily subscription expiry check at 01:00 UTC
    scheduler.add_job(
        lambda: __import__("asyncio").get_event_loop().create_task(run_daily_expiry_check(db)),
        "cron", hour=1, minute=0, id="daily_expiry"
    )

    # Daily settlement processing at 03:00 UTC
    scheduler.add_job(
        lambda: __import__("asyncio").get_event_loop().create_task(run_daily_settlement_processing(db)),
        "cron", hour=3, minute=0, id="daily_settlements"
    )

    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduled jobs started: backup(02:00), expiry(01:00), invoices(06:00), reminders(07:00), settlements(03:00) UTC")


@app.on_event("shutdown")
async def shutdown_db_client():
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
    await close_db()
