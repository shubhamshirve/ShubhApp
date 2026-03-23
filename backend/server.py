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
from pathlib import Path

from database import db, close_db
from routers.auth import router as auth_router
from routers.admin import router as admin_router
from routers.operator import router as operator_router
from routers.webhooks import router as webhooks_router
from routers.backup import router as backup_router, _do_backup
from routers.public import router as public_router
from routers.wallet import router as wallet_router
from routers.support import router as support_router
from services.global_settings_store import get_global_settings_doc
from services.scheduler_settings import DEFAULT_CRON_SCHEDULES, merge_cron_schedule_settings, split_cron_time

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _ensure_env_files():
    """Create the root env file with default keys when missing."""
    backend_dir = Path(__file__).resolve().parent
    root_dir = backend_dir.parent

    root_env = root_dir / ".env"
    if not root_env.exists():
        root_env.write_text(
            "\n".join(
                [
                    "DOMAIN=localhost",
                    "SERVER_IP=",
                    "MONGO_URI=mongodb://mongodb:27017/saas_db",
                    "CORS_ORIGINS=http://localhost:3000,http://localhost:8001,https://localhost,http://localhost",
                    "REACT_APP_BACKEND_URL=",
                    "MONGO_URL=mongodb://localhost:27017/saas_db",
                    "DB_NAME=saas_db",
                    "MONGO_ROOT_USERNAME=admin",
                    "MONGO_ROOT_PASSWORD=change-this-mongo-password",
                    "MONGO_BIND_ADDRESS=127.0.0.1",
                    "JWT_SECRET=change-this-to-a-strong-random-secret",
                    "RAZORPAY_KEY_ID=your_razorpay_key_id",
                    "RAZORPAY_KEY_SECRET=your_razorpay_key_secret",
                    "RESEND_API_KEY=",
                    "RESEND_FROM_EMAIL=",
                    "SMTP_HOST=",
                    "SMTP_PORT=587",
                    "SMTP_USERNAME=",
                    "SMTP_PASSWORD=",
                    "SMTP_FROM_EMAIL=",
                    "SMTP_USE_TLS=true",
                    "WHATSAPP_PHONE_NUMBER_ID=",
                    "WHATSAPP_ACCESS_TOKEN=",
                    "WHATSAPP_BUSINESS_ACCOUNT_ID=",
                    "BACKUP_PASSWORD=change-this-backup-password",
                    "",
                ]
            ),
            encoding="utf-8",
        )

# ── App & routers ───────────────────────────────────────────────────────────
app = FastAPI(title="Multi-Tenant SaaS Billing Platform")

app.include_router(auth_router,      prefix="/api")
app.include_router(admin_router,     prefix="/api")
app.include_router(operator_router,  prefix="/api")
app.include_router(webhooks_router,  prefix="/api")
app.include_router(backup_router,    prefix="/api")
app.include_router(public_router,    prefix="/api")
app.include_router(wallet_router,    prefix="/api")
app.include_router(support_router,   prefix="/api")

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


@app.post("/api/seed")
async def seed_data():
    """Seed initial admin, addons, and default SaaS plans (idempotent)."""
    _ensure_env_files()
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
             "status": "active", "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None},
            {"id": generate_id(), "name": "Pro", "monthly_price": 2500,
             "max_subscribers": 1000, "max_staff": 5, "trial_enabled": False, "trial_days": 0,
             "gst_applicable": True, "included_addons": [],
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
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
    from services.cron_service import (
        run_daily_invoice_generation,
        run_daily_reminder_processing,
        run_daily_expiry_check,
        run_daily_wallet_check,
    )

    async def run_daily_backup_job():
        await _do_backup("auto")

    def scheduler_listener(event):
        if event.exception:
            logger.exception("Scheduled job '%s' failed", event.job_id, exc_info=event.exception)
        else:
            logger.info("Scheduled job '%s' completed successfully", event.job_id)

    platform_settings = await get_global_settings_doc({"type": "platform"}, {"_id": 0}) or {}
    schedule = merge_cron_schedule_settings(platform_settings)

    backup_hour, backup_minute = split_cron_time(schedule["cron_backup_time"])
    expiry_hour, expiry_minute = split_cron_time(schedule["cron_expiry_time"])
    invoice_hour, invoice_minute = split_cron_time(schedule["cron_invoice_time"])
    wallet_hour, wallet_minute = split_cron_time(schedule["cron_wallet_time"])
    reminder_hour, reminder_minute = split_cron_time(schedule["cron_reminder_time"])

    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_listener(scheduler_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # Daily auto-backup at 03:00 IST
    scheduler.add_job(
        run_daily_backup_job,
        "cron",
        hour=backup_hour,
        minute=backup_minute,
        id="daily_backup",
        coalesce=True,
        misfire_grace_time=3600,
    )

    # Daily auto-invoice generation at 08:00 IST
    scheduler.add_job(
        run_daily_invoice_generation,
        "cron",
        hour=invoice_hour,
        minute=invoice_minute,
        id="daily_invoices",
        args=[db],
        coalesce=True,
        misfire_grace_time=3600,
    )

    # Daily scheduled reminder processing at 10:00 IST
    scheduler.add_job(
        run_daily_reminder_processing,
        "cron",
        hour=reminder_hour,
        minute=reminder_minute,
        id="daily_reminders",
        args=[db],
        coalesce=True,
        misfire_grace_time=3600,
    )

    # Daily subscription expiry check at 00:05 IST
    scheduler.add_job(
        run_daily_expiry_check,
        "cron",
        hour=expiry_hour,
        minute=expiry_minute,
        id="daily_expiry",
        args=[db],
        coalesce=True,
        misfire_grace_time=3600,
    )

    # Daily wallet balance check at 09:00 IST
    scheduler.add_job(
        run_daily_wallet_check,
        "cron",
        hour=wallet_hour,
        minute=wallet_minute,
        id="daily_wallet_check",
        args=[db],
        coalesce=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    app.state.scheduler = scheduler
    for job in scheduler.get_jobs():
        logger.info("Scheduled job registered: id=%s next_run=%s", job.id, job.next_run_time)
    logger.info(
        "Scheduled jobs started (Asia/Kolkata IST): backup(%s), expiry(%s), invoices(%s), reminders(%s), wallet_check(%s)",
        schedule["cron_backup_time"],
        schedule["cron_expiry_time"],
        schedule["cron_invoice_time"],
        schedule["cron_reminder_time"],
        schedule["cron_wallet_time"],
    )


@app.on_event("shutdown")
async def shutdown_db_client():
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
    await close_db()
