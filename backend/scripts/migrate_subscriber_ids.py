#!/usr/bin/env python3
"""
One-time migration: UUID subscriber IDs → short EB-format IDs (e.g. EB4K7X2M9Q)

Collections updated:
  - subscribers : id field
  - invoices    : subscriber_id field

Usage (from backend directory or inside container):
  python scripts/migrate_subscriber_ids.py           # live migration
  python scripts/migrate_subscriber_ids.py --dry-run # preview only
"""
import asyncio
import os
import re
import secrets
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Load env ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import db, client, mongo_url as MONGO_URL, db_name as DB_NAME

# UUID pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

ALPHABET = string.ascii_uppercase + string.digits  # A-Z 0-9


async def _gen_unique_id(db) -> str:
    for _ in range(30):
        suffix = "".join(secrets.choice(ALPHABET) for _ in range(8))
        new_id = f"EB{suffix}"
        if not await db.subscribers.find_one({"id": new_id}, {"_id": 1}):
            return new_id
    ts = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S%f")
    return f"EB{ts[:8].upper()}"


async def run_migration(dry_run: bool = False) -> dict:
    mode = "[DRY RUN]" if dry_run else "[LIVE]"
    print(f"\n{mode} Subscriber ID migration — DB: {DB_NAME}")
    print(f"  MongoDB : {MONGO_URL}\n")

    all_subs  = await db.subscribers.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(None)
    uuid_subs = [s for s in all_subs if UUID_PATTERN.match(s.get("id", ""))]

    print(f"  Total subscribers  : {len(all_subs)}")
    print(f"  Need migration     : {len(uuid_subs)}")
    print(f"  Already EB-format  : {len(all_subs) - len(uuid_subs)}\n")

    if not uuid_subs:
        print("[OK] Nothing to migrate.\n")
        client.close()
        return {"migrated": 0, "errors": [], "mapping": {}}

    migrated = 0
    errors   = []
    mapping  = {}  # old_id → new_id

    for sub in uuid_subs:
        old_id = sub["id"]
        name   = sub.get("name", "unknown")[:35]
        new_id = await _gen_unique_id(db)
        mapping[old_id] = new_id

        print(f"  {name:<35s}  {old_id}  ->  {new_id}")

        if dry_run:
            migrated += 1
            continue

        try:
            s_res = await db.subscribers.update_one(
                {"id": old_id}, {"$set": {"id": new_id}}
            )
            i_res = await db.invoices.update_many(
                {"subscriber_id": old_id}, {"$set": {"subscriber_id": new_id}}
            )
            print(f"    [OK]  subscriber updated | invoices updated: {i_res.modified_count}")
            migrated += 1
        except Exception as exc:
            msg = f"{old_id}: {exc}"
            print(f"    [ERROR]  {msg}")
            errors.append(msg)

    # ── Write log ──────────────────────────────────────────────────────────
    if not dry_run and mapping:
        log_file = Path(__file__).parent / "migration_subscriber_ids.log"
        with open(log_file, "w") as f:
            f.write(f"# Subscriber ID migration — {datetime.now(timezone.utc).isoformat()}\n")
            f.write("# old_uuid\tnew_eb_id\n")
            for old, new in mapping.items():
                f.write(f"{old}\t{new}\n")
        print(f"\n  Log saved → {log_file}")

    print(f"\n{'='*60}")
    print(f"{mode} Done — migrated: {migrated}  errors: {len(errors)}\n")

    client.close()
    return {"migrated": migrated, "errors": errors, "mapping": mapping}


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_migration(dry_run=dry_run))
