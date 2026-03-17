"""Input sanitization helpers for API request data."""
from __future__ import annotations

import os
import re
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, field_validator


def sanitize_text(value: str, *, trim: bool = True) -> str:
    """Normalize user input by removing control characters and outer whitespace."""
    cleaned = "".join(
        ch for ch in value
        if ch in ("\n", "\r", "\t") or ord(ch) >= 32
    ).replace("\x7f", "")
    return cleaned.strip() if trim else cleaned


def sanitize_value(value: Any, *, trim: bool = True) -> Any:
    """Recursively sanitize strings nested inside common container types."""
    if isinstance(value, str):
        return sanitize_text(value, trim=trim)
    if isinstance(value, list):
        return [sanitize_value(item, trim=trim) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_value(item, trim=trim) for item in value)
    if isinstance(value, dict):
        return {key: sanitize_value(item, trim=trim) for key, item in value.items()}
    return value


class SanitizedModel(BaseModel):
    """Base request model that sanitizes string fields before validation."""

    model_config = ConfigDict(str_strip_whitespace=True)
    _unsanitized_fields: ClassVar[set[str]] = set()

    @field_validator("*", mode="before")
    @classmethod
    def sanitize_fields(cls, value: Any, info) -> Any:
        if info.field_name in cls._unsanitized_fields:
            return value
        return sanitize_value(value)


def sanitize_filename(filename: str, *, default: str = "upload") -> str:
    """Keep only a safe basename for uploaded files."""
    base = os.path.basename(filename or "")
    stem, ext = os.path.splitext(base)
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or default
    safe_ext = re.sub(r"[^A-Za-z0-9.]+", "", ext)[:10]
    return f"{safe_stem}{safe_ext}"
