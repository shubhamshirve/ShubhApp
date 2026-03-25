import os
import secrets
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from services.global_settings_store import get_global_setting, save_global_setting

async def get_env_setting(key: str, default: Any = None) -> Any:
    """
    Fetches a setting from the database 'env_settings' document.
    Falls back to environment variables if not found in database.
    
    Priority:
    1. global_settings collection -> type="env_settings"
    2. Legacy collections (optional specific fallbacks)
    3. os.environ
    """
    # 1. Check database for new env_settings
    db_settings = await get_global_setting("env_settings")
    if db_settings and key in db_settings:
        val = db_settings[key]
        if val: # Only return if not empty string
            return val

    # 2. Legacy fallbacks
    if key.startswith("whatsapp_"):
        # Check platform_whatsapp collection
        wa_config = await get_global_setting("platform_whatsapp")
        if wa_config:
            sub_key = key.replace("whatsapp_", "")
            if sub_key in wa_config:
                return wa_config[sub_key]

    # 3. Environment variables
    env_key = key.upper()
    return os.environ.get(env_key, default)

async def set_env_setting(key: str, value: Any):
    """Updates a setting in the database env_settings document."""
    db_settings = await get_global_setting("env_settings") or {}
    db_settings[key] = value
    await save_global_setting("env_settings", db_settings)

async def get_jwt_secret() -> str:
    """Retrieves the JWT secret, generating one if missing from both DB and Env."""
    secret = await get_env_setting("jwt_secret")
    if not secret:
        # If missing everywhere, generate a persistent one in DB
        secret = secrets.token_urlsafe(32)
        await set_env_setting("jwt_secret", secret)
        logger.warning("Generated new JWT_SECRET and saved to database")
    return secret

async def get_backup_password() -> str:
    """Retrieves the backup encryption password."""
    return await get_env_setting("backup_password", "ebill_default_bk_pw_2024")
