"""Admin backup & restore system with scheduled daily backups."""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
import json
import gzip
import os
import logging

from database import db
from dependencies import require_admin
from utils import generate_id

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("/app/backups")
BACKUP_PASSWORD = os.environ.get("BACKUP_PASSWORD", "Shubham@123")

COLLECTIONS = [
    "users", "operators", "saas_plans", "operator_plans", "subscribers",
    "invoices", "addons", "payment_gateways", "whatsapp_configs",
    "announcements", "audit_logs", "global_settings", "invoice_settings",
    "saas_payments", "checkout_orders", "notification_queue", "backups",
]

router = APIRouter(prefix="/admin/backup", tags=["Backup"])


class RestoreRequest(BaseModel):
    password: str


# ── Internal helpers ────────────────────────────────────────────────────────

async def _do_backup(backup_type: str = "manual") -> dict:
    """Dump all collections to a gzipped JSON file and record metadata."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_id = generate_id()
    now = datetime.now(timezone.utc)

    payload: dict = {
        "backup_id": backup_id,
        "created_at": now.isoformat(),
        "collections": {},
    }

    for col in COLLECTIONS:
        if col == "backups":
            continue  # skip backup meta-collection from the dump
        docs = await db[col].find({}, {"_id": 0}).to_list(200_000)
        payload["collections"][col] = docs

    filename = f"backup_{now.strftime('%Y%m%d_%H%M%S')}_{backup_id[:8]}.json.gz"
    filepath = BACKUP_DIR / filename

    with gzip.open(filepath, "wt", encoding="utf-8") as f:
        json.dump(payload, f)

    size_bytes = filepath.stat().st_size
    total_records = sum(len(v) for v in payload["collections"].values())

    meta = {
        "id": backup_id,
        "filename": filename,
        "created_at": now.isoformat(),
        "size_bytes": size_bytes,
        "size_kb": round(size_bytes / 1024, 1),
        "type": backup_type,
        "total_records": total_records,
        "collections": list(payload["collections"].keys()),
    }
    await db.backups.insert_one(meta)
    logger.info(f"Backup created: {filename} ({size_bytes} bytes, {total_records} records)")
    return meta


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/create")
async def create_backup(current_user: dict = Depends(require_admin)):
    """Manually create a full database backup."""
    meta = await _do_backup("manual")
    meta.pop("_id", None)
    return {"message": "Backup created successfully", "backup": meta}


@router.get("/list")
async def list_backups(current_user: dict = Depends(require_admin)):
    """List all available backups."""
    backups = await db.backups.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return backups


@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: str,
    body: RestoreRequest,
    current_user: dict = Depends(require_admin),
):
    """Restore from a backup after password confirmation."""
    if body.password != BACKUP_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid backup password")

    meta = await db.backups.find_one({"id": backup_id}, {"_id": 0})
    if not meta:
        raise HTTPException(status_code=404, detail="Backup not found")

    filepath = BACKUP_DIR / meta["filename"]
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found on disk")

    with gzip.open(filepath, "rt", encoding="utf-8") as f:
        data = json.load(f)

    restored = []
    for col, docs in data["collections"].items():
        await db[col].delete_many({})
        if docs:
            await db[col].insert_many(docs)
        restored.append(col)

    logger.info(f"Restored backup {backup_id} — {len(restored)} collections")
    return {
        "message": "Backup restored successfully",
        "backup_id": backup_id,
        "collections_restored": restored,
        "records_restored": sum(len(data["collections"].get(c, [])) for c in restored),
    }


@router.get("/download/{backup_id}")
async def download_backup(backup_id: str, current_user: dict = Depends(require_admin)):
    """Download a backup file as a gzipped JSON attachment."""
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
    meta = await db.backups.find_one({"id": backup_id}, {"_id": 0})
    if not meta:
        raise HTTPException(status_code=404, detail="Backup not found")

    filepath = BACKUP_DIR / meta["filename"]
    if filepath.exists():
        filepath.unlink()

    await db.backups.delete_one({"id": backup_id})
    return {"message": "Backup deleted"}
