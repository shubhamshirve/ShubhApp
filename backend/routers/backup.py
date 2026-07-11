"""Admin backup & restore system with scheduled daily backups."""
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from fastapi.responses import FileResponse
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import gzip
import io
import os
import logging

from database import db
from dependencies import require_admin
from utils import generate_id
from sanitization import SanitizedModel, sanitize_text

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("/app/backups")
BACKUP_PASSWORD = os.environ.get("BACKUP_PASSWORD", "Shubham@123")
BACKUP_RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))

# ── Collections included in every backup ────────────────────────────────────
# Ordered logically: core accounts → billing → settings → comms → audit
COLLECTIONS = [
    # Core accounts & access
    "users",
    "operators",
    "operator_wallets",        # wallet balances per operator
    "wallet_transactions",     # full recharge / deduction history

    # SaaS plans & subscriptions
    "saas_plans",
    "operator_plans",
    "addons",

    # Subscriber & billing
    "subscribers",
    "invoices",
    "invoice_settings",        # per-operator invoice branding
    "operator_theme",          # per-operator colour theme / logo

    # Payments & checkout
    "payment_gateways",
    "saas_payments",
    "checkout_orders",
    "discount_codes",

    # Platform & admin settings
    # global_settings stores: env_settings (jwt_secret, backup_password),
    # platform config, platform_whatsapp, reminder_settings, cron times,
    # landing page content, whatsapp_template_settings, etc.
    "global_settings",

    # WhatsApp
    "whatsapp_templates",
    "whatsapp_message_logs",

    # Communications
    "announcements",
    "notification_queue",

    # Audit & logs
    "audit_logs",
    "error_logs",
    "webhook_events",          # Razorpay / WhatsApp webhook audit trail

    # Support
    "support_tickets",
    "support_replies",

    # Backup metadata — always skipped from dump (restored separately via meta)
    "backups",
]

# ── Transient collections: cleared on restore, never backed up ───────────────
# These hold short-lived state that is invalid on a new / restored server.
TRANSIENT_COLLECTIONS = [
    "background_jobs",         # in-flight async job queue
    "password_recovery",       # email OTPs (expire in minutes)
    "pending_registrations",   # unverified registration tokens
]

router = APIRouter(prefix="/admin/backup", tags=["Backup"])


class RestoreRequest(SanitizedModel):
    _unsanitized_fields = {"password"}
    password: str


# ── Internal helpers ────────────────────────────────────────────────────────

async def _do_backup(backup_type: str = "manual") -> dict:
    """Dump all collections to a gzipped JSON file and record metadata."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_id = generate_id()
    now = datetime.now(timezone.utc)

    payload: dict = {
        "backup_id": backup_id,
        "backup_type": backup_type,
        "created_at": now.isoformat(),
        "schema_version": 2,          # bump when backup format changes
        "collections": {},
        "collection_counts": {},      # per-collection record count for quick inspection
    }

    for col in COLLECTIONS:
        if col == "backups":
            continue  # backup metadata is rebuilt from files, not restored
        docs = await db[col].find({}, {"_id": 0}).to_list(200_000)
        payload["collections"][col] = docs
        payload["collection_counts"][col] = len(docs)

    filename = f"backup_{now.strftime('%Y%m%d_%H%M%S')}_{backup_id[:8]}.json.gz"
    filepath = BACKUP_DIR / filename

    with gzip.open(filepath, "wt", encoding="utf-8") as f:
        json.dump(payload, f)

    size_bytes = filepath.stat().st_size
    total_records = sum(payload["collection_counts"].values())

    meta = {
        "id": backup_id,
        "filename": filename,
        "created_at": now.isoformat(),
        "size_bytes": size_bytes,
        "size_kb": round(size_bytes / 1024, 1),
        "type": backup_type,
        "total_records": total_records,
        "collections": list(payload["collections"].keys()),
        "collection_counts": payload["collection_counts"],
    }
    await db.backups.insert_one(meta)
    logger.info(
        "Backup created: %s (%d bytes, %d records across %d collections)",
        filename, size_bytes, total_records, len(payload["collections"])
    )
    return meta


async def _sync_backups_from_disk() -> int:
    """Recover backup metadata from files when a file exists but DB metadata is missing."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    known = {
        item["filename"]: item
        for item in await db.backups.find({}, {"_id": 0, "filename": 1}).to_list(1000)
    }
    synced = 0

    for filepath in BACKUP_DIR.glob("backup_*.json.gz"):
        if filepath.name in known:
            continue

        try:
            with gzip.open(filepath, "rt", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as exc:
            logger.warning("Skipping backup metadata recovery for %s: %s", filepath.name, exc)
            continue

        collections = payload.get("collections") or {}
        size_bytes = filepath.stat().st_size
        meta = {
            "id": payload.get("backup_id") or generate_id(),
            "filename": filepath.name,
            "created_at": payload.get("created_at") or datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc).isoformat(),
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 1),
            "type": payload.get("backup_type", "auto"),
            "total_records": sum(len(v) for v in collections.values()),
            "collections": list(collections.keys()),
        }
        await db.backups.insert_one(meta)
        synced += 1

    return synced


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/create")
async def create_backup(current_user: dict = Depends(require_admin)):
    """Manually create a full database backup."""
    meta = await _do_backup("manual")
    meta.pop("_id", None)
    return {"message": "Backup created successfully", "backup": meta}


@router.get("/list")
async def list_backups(
    page: int = 1,
    per_page: int = 10,
    current_user: dict = Depends(require_admin),
):
    """List all available backups with pagination and aggregate stats."""
    await _sync_backups_from_disk()
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    total = await db.backups.count_documents({})
    skip = (page - 1) * per_page
    backups = await db.backups.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(per_page).to_list(per_page)

    # Aggregate stats across ALL backups (not just current page)
    pipeline = [
        {"$group": {
            "_id": None,
            "total_size_kb": {"$sum": "$size_kb"},
            "auto_count": {"$sum": {"$cond": [{"$eq": ["$type", "auto"]}, 1, 0]}},
            "manual_count": {"$sum": {"$cond": [{"$eq": ["$type", "manual"]}, 1, 0]}},
        }}
    ]
    agg = await db.backups.aggregate(pipeline).to_list(1)
    stats = agg[0] if agg else {"total_size_kb": 0, "auto_count": 0, "manual_count": 0}

    return {
        "backups": backups,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
        "stats": {
            "total_size_kb": round(stats.get("total_size_kb", 0), 1),
            "auto_count": stats.get("auto_count", 0),
            "manual_count": stats.get("manual_count", 0),
            "retention_days": BACKUP_RETENTION_DAYS,
        },
    }


@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: str,
    body: RestoreRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Restore from a backup after password confirmation.

    Safe to use on a fresh server:
      1. Wipes all existing data in backed-up collections
      2. Restores every collection from the backup file
      3. Clears transient collections (background_jobs, password_recovery,
         pending_registrations) so the new server starts clean
      4. NOTE: You will need to log in again after restore — user sessions
         are invalidated when the users collection is replaced.
    """
    backup_id = sanitize_text(backup_id)

    # Allow password from env OR from global_settings (db-stored override)
    from services.env_service import get_backup_password
    valid_password = await get_backup_password()
    if body.password != valid_password:
        raise HTTPException(status_code=403, detail="Invalid backup password")

    meta = await db.backups.find_one({"id": backup_id}, {"_id": 0})
    if not meta:
        raise HTTPException(status_code=404, detail="Backup not found")

    filepath = BACKUP_DIR / meta["filename"]
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found on disk")

    with gzip.open(filepath, "rt", encoding="utf-8") as f:
        data = json.load(f)

    if "collections" not in data:
        raise HTTPException(status_code=422, detail="Invalid backup file: missing collections key")

    restored = []
    skipped = []
    records_restored = 0

    for col, docs in data["collections"].items():
        # Never restore backup metadata — it gets rebuilt from disk
        if col == "backups":
            skipped.append(col)
            continue
        try:
            await db[col].delete_many({})
            if docs:
                await db[col].insert_many(docs)
                records_restored += len(docs)
            restored.append(col)
        except Exception as exc:
            logger.error("Failed to restore collection %s: %s", col, exc)
            skipped.append(col)

    # Clear transient collections — stale state must not survive to new server
    for col in TRANSIENT_COLLECTIONS:
        try:
            await db[col].delete_many({})
        except Exception:
            pass

    logger.info(
        "Restore complete — backup_id=%s, collections=%d, records=%d, skipped=%s",
        backup_id, len(restored), records_restored, skipped
    )
    return {
        "message": "Backup restored successfully",
        "backup_id": backup_id,
        "collections_restored": restored,
        "collections_skipped": skipped,
        "records_restored": records_restored,
        "note": "Session invalidated — please log in again with your restored credentials.",
    }


@router.get("/download/{backup_id}")
async def download_backup(backup_id: str, current_user: dict = Depends(require_admin)):
    """Download a backup file as a gzipped JSON attachment."""
    backup_id = sanitize_text(backup_id)
    meta = await db.backups.find_one({"id": backup_id}, {"_id": 0})
    if not meta:
        raise HTTPException(status_code=404, detail="Backup not found")

    filepath = BACKUP_DIR / meta["filename"]
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found on disk")

    return FileResponse(
        path=str(filepath),
        media_type="application/gzip",
        filename=meta["filename"],
        headers={"Content-Disposition": f"attachment; filename={meta['filename']}"},
    )


@router.delete("/{backup_id}")
async def delete_backup(backup_id: str, current_user: dict = Depends(require_admin)):
    """Delete a backup file and its metadata."""
    backup_id = sanitize_text(backup_id)
    meta = await db.backups.find_one({"id": backup_id}, {"_id": 0})
    if not meta:
        raise HTTPException(status_code=404, detail="Backup not found")

    filepath = BACKUP_DIR / meta["filename"]
    if filepath.exists():
        filepath.unlink()

    await db.backups.delete_one({"id": backup_id})
    return {"message": "Backup deleted"}


@router.post("/upload")
async def upload_backup(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """Upload a previously downloaded .json.gz backup file and register it."""
    if not (file.filename or "").endswith(".json.gz"):
        raise HTTPException(status_code=400, detail="Only .json.gz backup files are accepted")

    content = await file.read()

    # Validate the file is a proper gzipped JSON backup
    try:
        with gzip.open(io.BytesIO(content), "rt", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid backup file: not a valid gzipped JSON archive")

    if "collections" not in payload:
        raise HTTPException(status_code=400, detail="Invalid backup format: missing 'collections' key")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Sanitize filename — strip path traversal characters
    safe_filename = (
        (file.filename or "")
        .replace("..", "")
        .replace("/", "")
        .replace("\\", "")
        .strip()
    ) or f"uploaded_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json.gz"

    filepath = BACKUP_DIR / safe_filename
    # Avoid overwriting existing files by appending a timestamp suffix
    if filepath.exists():
        base = safe_filename[:-8]  # strip .json.gz
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        safe_filename = f"{base}_imported_{ts}.json.gz"
        filepath = BACKUP_DIR / safe_filename

    with open(filepath, "wb") as f:
        f.write(content)

    collections = payload.get("collections") or {}
    collection_counts = payload.get("collection_counts") or {k: len(v) for k, v in collections.items()}
    backup_id = payload.get("backup_id") or generate_id()

    # Avoid duplicate IDs in DB
    if await db.backups.find_one({"id": backup_id}):
        backup_id = generate_id()

    size_bytes = filepath.stat().st_size
    meta = {
        "id": backup_id,
        "filename": safe_filename,
        "created_at": payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "size_bytes": size_bytes,
        "size_kb": round(size_bytes / 1024, 1),
        "type": "uploaded",
        "total_records": sum(collection_counts.values()),
        "collections": list(collections.keys()),
        "collection_counts": collection_counts,
    }
    await db.backups.insert_one(meta)
    meta.pop("_id", None)

    logger.info(f"Backup uploaded: {safe_filename} ({size_bytes} bytes)")
    return {"message": "Backup uploaded successfully", "backup": meta}


# ── Auto-purge helpers ───────────────────────────────────────────────────────

async def _purge_old_backups(max_age_days: int = BACKUP_RETENTION_DAYS) -> dict:
    """Delete backups (file + DB record) older than max_age_days.
    Returns a summary of what was deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    cutoff_iso = cutoff.isoformat()

    old_backups = await db.backups.find(
        {"created_at": {"$lt": cutoff_iso}}, {"_id": 0}
    ).to_list(1000)

    deleted_files, deleted_db, errors = 0, 0, []
    for meta in old_backups:
        filepath = BACKUP_DIR / meta["filename"]
        try:
            if filepath.exists():
                filepath.unlink()
                deleted_files += 1
        except Exception as e:
            errors.append(f"File delete error {meta['filename']}: {e}")
        try:
            await db.backups.delete_one({"id": meta["id"]})
            deleted_db += 1
        except Exception as e:
            errors.append(f"DB delete error {meta['id']}: {e}")

    logger.info(
        f"Purged {deleted_db} old backups (>{max_age_days}d) | "
        f"files removed: {deleted_files} | errors: {len(errors)}"
    )
    return {
        "purged_count": deleted_db,
        "files_removed": deleted_files,
        "retention_days": max_age_days,
        "cutoff_date": cutoff_iso,
        "errors": errors,
    }


@router.post("/purge-old")
async def purge_old_backups(
    retention_days: int = BACKUP_RETENTION_DAYS,
    current_user: dict = Depends(require_admin),
):
    """Manually trigger deletion of all backups older than retention_days (default: 30)."""
    retention_days = max(1, min(retention_days, 365))
    result = await _purge_old_backups(retention_days)
    return {"message": f"Purged {result['purged_count']} backups older than {retention_days} days", **result}
