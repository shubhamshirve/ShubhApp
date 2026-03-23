"""Shared scheduler timing helpers for admin settings and app startup."""
from datetime import datetime

DEFAULT_CRON_SCHEDULES = {
    "cron_backup_time": "03:00",
    "cron_expiry_time": "00:05",
    "cron_invoice_time": "08:00",
    "cron_wallet_time": "09:00",
    "cron_reminder_time": "10:00",
}


def normalize_cron_time(value: str, default: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return default
    try:
        parsed = datetime.strptime(raw, "%H:%M")
    except ValueError as exc:
        raise ValueError("Cron time must be in HH:MM 24-hour format") from exc
    return parsed.strftime("%H:%M")


def split_cron_time(value: str) -> tuple[int, int]:
    hour_str, minute_str = value.split(":")
    return int(hour_str), int(minute_str)


def merge_cron_schedule_settings(settings: dict | None) -> dict:
    settings = settings or {}
    merged = {}
    for key, default in DEFAULT_CRON_SCHEDULES.items():
        merged[key] = normalize_cron_time(settings.get(key, default), default)
    return merged
