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

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import os
import logging

from database import db, close_db
from routers.auth import router as auth_router
from routers.admin import router as admin_router
from routers.operator import router as operator_router
from routers.webhooks import router as webhooks_router
from routers.backup import router as backup_router, _do_backup

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

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Misc endpoints ──────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Multi-Tenant SaaS Billing Platform"}


@app.post("/api/seed")
async def seed_data():
    """Seed initial admin account and default SaaS plans (idempotent)."""
    from utils import generate_id, hash_password
    from datetime import datetime, timezone

    if await db.users.find_one({"role": "admin", "deleted_at": None}):
        return {"message": "Data already seeded"}

    now = datetime.now(timezone.utc)
    admin_user = {
        "id": generate_id(), "email": "admin@saas.com", "name": "Super Admin",
        "phone": "9999999999", "password": hash_password("admin123"),
        "role": "admin", "operator_id": None, "status": "active",
        "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None
    }
    await db.users.insert_one(admin_user)

    plans = [
        {"id": generate_id(), "name": "Starter (Trial)", "monthly_price": 0,
         "max_subscribers": 10, "max_staff": 1, "trial_enabled": True, "trial_days": 3,
         "notification_module": False, "auto_reminder": False, "audit_logs": False,
         "payment_gateway_setup": False, "gst_applicable": False, "included_addons": [],
         "status": "active", "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None},
        {"id": generate_id(), "name": "Basic", "monthly_price": 999,
         "max_subscribers": 100, "max_staff": 3, "trial_enabled": False, "trial_days": 0,
         "notification_module": True, "auto_reminder": True, "audit_logs": False,
         "payment_gateway_setup": True, "gst_applicable": True, "included_addons": [],
         "status": "active", "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None},
        {"id": generate_id(), "name": "Professional", "monthly_price": 2499,
         "max_subscribers": 500, "max_staff": 10, "trial_enabled": False, "trial_days": 0,
         "notification_module": True, "auto_reminder": True, "audit_logs": True,
         "payment_gateway_setup": True, "gst_applicable": True, "included_addons": [],
         "status": "active", "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None},
        {"id": generate_id(), "name": "Enterprise", "monthly_price": 4999,
         "max_subscribers": 2000, "max_staff": 25, "trial_enabled": False, "trial_days": 0,
         "notification_module": True, "auto_reminder": True, "audit_logs": True,
         "payment_gateway_setup": True, "gst_applicable": True, "included_addons": [],
         "status": "active", "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None},
    ]
    await db.saas_plans.insert_many(plans)

    return {"message": "Data seeded successfully", "admin_email": "admin@saas.com", "admin_password": "admin123"}


# ── Shutdown ────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Start the daily auto-backup scheduler."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    # Run daily at 02:00 UTC
    scheduler.add_job(
        lambda: __import__("asyncio").get_event_loop().create_task(_do_backup("auto")),
        "cron", hour=2, minute=0, id="daily_backup"
    )
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Daily auto-backup scheduler started (02:00 UTC)")


@app.on_event("shutdown")
async def shutdown_db_client():
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
    await close_db()
