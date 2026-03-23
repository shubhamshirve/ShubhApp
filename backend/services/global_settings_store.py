"""Helpers for reading and maintaining singleton documents in global_settings."""
from __future__ import annotations

from typing import Any

from database import db


def _settings_sort():
    return [("updated_at", -1), ("created_at", -1), ("_id", -1)]


async def get_global_settings_doc(selector: dict[str, Any], projection: dict[str, int] | None = None) -> dict[str, Any] | None:
    docs = await db.global_settings.find(selector, projection).sort(_settings_sort()).to_list(1)
    return docs[0] if docs else None


async def save_global_settings_doc(selector: dict[str, Any], data: dict[str, Any]) -> None:
    docs = await db.global_settings.find(selector, {"_id": 1}).sort(_settings_sort()).to_list(100)
    if docs:
        primary_id = docs[0]["_id"]
        await db.global_settings.update_one({"_id": primary_id}, {"$set": data}, upsert=False)
        duplicate_ids = [doc["_id"] for doc in docs[1:]]
        if duplicate_ids:
            await db.global_settings.delete_many({"_id": {"$in": duplicate_ids}})
        return

    await db.global_settings.insert_one(data)
