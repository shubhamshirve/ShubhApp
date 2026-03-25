"""
Generate .env file from database settings for application deployment.

This utility handles creating and updating the .env file with settings from:
1. Global settings collection (type=env_settings)
2. Email settings collection
3. WhatsApp configuration  
4. Default values for new installations

Usage:
    python -c "from services.env_generator import generate_env_file; generate_env_file()"
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any


async def generate_env_file_async(root_dir: Optional[Path] = None) -> str:
    """
    Generate .env file from database settings.
    
    Args:
        root_dir: Root directory for .env file. Defaults to workspace root.
    
    Returns:
        Path to generated .env file
    """
    if root_dir is None:
        # Get root directory (parent of backend)
        backend_dir = Path(__file__).resolve().parent.parent
        root_dir = backend_dir.parent
    
    root_env = root_dir / ".env"
    
    # Build env content from database and environment variables
    env_lines = [
        "# E-Bill Platform Environment Configuration",
        "# Generated from admin settings",
        "",
    ]
    
    # Import here to avoid circular imports
    from services.global_settings_store import get_global_settings_doc
    from services.email_service import get_email_service_async
    env_lines.extend([
        f"DOMAIN={os.environ.get('DOMAIN', 'localhost')}",
        f"SERVER_IP={os.environ.get('SERVER_IP', '')}",
        f"MONGO_URI={os.environ.get('MONGO_URI', 'mongodb://mongodb:27017/saas_db')}",
        f"CORS_ORIGINS={os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8001,https://localhost,http://localhost')}",
        f"REACT_APP_BACKEND_URL={os.environ.get('REACT_APP_BACKEND_URL', '')}",
        f"MONGO_URL={os.environ.get('MONGO_URL', 'mongodb://localhost:27017/saas_db')}",
        f"DB_NAME={os.environ.get('DB_NAME', 'saas_db')}",
        f"MONGO_ROOT_USERNAME={os.environ.get('MONGO_ROOT_USERNAME', 'admin')}",
        f"MONGO_ROOT_PASSWORD={os.environ.get('MONGO_ROOT_PASSWORD', 'change-this-mongo-password')}",
        f"MONGO_BIND_ADDRESS={os.environ.get('MONGO_BIND_ADDRESS', '127.0.0.1')}",
        "",
    ])
    
    # Security settings from database
    try:
        env_settings = await get_global_settings_doc({"type": "env_settings"}, {"_id": 0})
        if env_settings:
            env_lines.extend([
                "# Security Settings (from Admin Settings > Security tab)",
                f"JWT_SECRET={env_settings.get('jwt_secret', os.environ.get('JWT_SECRET', 'change-this-to-a-strong-random-secret'))}",
                f"BACKUP_PASSWORD={env_settings.get('backup_password', os.environ.get('BACKUP_PASSWORD', 'change-this-backup-password'))}",
                "",
            ])
        else:
            env_lines.extend([
                "# Security Settings (configure in Admin Settings > Security tab)",
                f"JWT_SECRET={os.environ.get('JWT_SECRET', 'change-this-to-a-strong-random-secret')}",
                f"BACKUP_PASSWORD={os.environ.get('BACKUP_PASSWORD', 'change-this-backup-password')}",
                "",
            ])
    except Exception:
        env_lines.extend([
            "# Security Settings",
            f"JWT_SECRET={os.environ.get('JWT_SECRET', 'change-this-to-a-strong-random-secret')}",
            f"BACKUP_PASSWORD={os.environ.get('BACKUP_PASSWORD', 'change-this-backup-password')}",
            "",
        ])
    
    # Email settings
    try:
        email_doc = await get_global_settings_doc({"key": "email_settings"}, {"_id": 0})
        if email_doc:
            env_lines.extend([
                "# Email Configuration (from Admin Settings > Email API tab)",
                f"RESEND_API_KEY={email_doc.get('resend_api_key', '')}",
                f"RESEND_FROM_EMAIL={email_doc.get('resend_from_email', '')}",
                f"SMTP_HOST={email_doc.get('smtp_host', '')}",
                f"SMTP_PORT={email_doc.get('smtp_port', '587')}",
                f"SMTP_USERNAME={email_doc.get('smtp_username', '')}",
                f"SMTP_PASSWORD={email_doc.get('smtp_password', '')}",
                f"SMTP_FROM_EMAIL={email_doc.get('smtp_from_email', '')}",
                f"SMTP_USE_TLS={str(email_doc.get('smtp_use_tls', True)).lower()}",
                "",
            ])
        else:
            env_lines.extend([
                "# Email Configuration (configure in Admin Settings > Email API tab)",
                f"RESEND_API_KEY={os.environ.get('RESEND_API_KEY', '')}",
                f"RESEND_FROM_EMAIL={os.environ.get('RESEND_FROM_EMAIL', '')}",
                f"SMTP_HOST={os.environ.get('SMTP_HOST', '')}",
                f"SMTP_PORT={os.environ.get('SMTP_PORT', '587')}",
                f"SMTP_USERNAME={os.environ.get('SMTP_USERNAME', '')}",
                f"SMTP_PASSWORD={os.environ.get('SMTP_PASSWORD', '')}",
                f"SMTP_FROM_EMAIL={os.environ.get('SMTP_FROM_EMAIL', '')}",
                f"SMTP_USE_TLS={os.environ.get('SMTP_USE_TLS', 'true').lower()}",
                "",
            ])
    except Exception:
        env_lines.extend([
            "# Email Configuration",
            f"RESEND_API_KEY={os.environ.get('RESEND_API_KEY', '')}",
            f"RESEND_FROM_EMAIL={os.environ.get('RESEND_FROM_EMAIL', '')}",
            f"SMTP_HOST={os.environ.get('SMTP_HOST', '')}",
            f"SMTP_PORT={os.environ.get('SMTP_PORT', '587')}",
            f"SMTP_USERNAME={os.environ.get('SMTP_USERNAME', '')}",
            f"SMTP_PASSWORD={os.environ.get('SMTP_PASSWORD', '')}",
            f"SMTP_FROM_EMAIL={os.environ.get('SMTP_FROM_EMAIL', '')}",
            f"SMTP_USE_TLS={os.environ.get('SMTP_USE_TLS', 'true').lower()}",
            "",
        ])
    
    # WhatsApp settings
    try:
        wa_config = await get_global_settings_doc({"type": "platform_whatsapp"}, {"_id": 0})
        if wa_config:
            env_lines.extend([
                "# WhatsApp Configuration (from Admin Settings > WhatsApp tab)",
                f"WHATSAPP_PHONE_NUMBER_ID={wa_config.get('phone_number_id', '')}",
                f"WHATSAPP_ACCESS_TOKEN={wa_config.get('access_token', '')}",
                f"WHATSAPP_BUSINESS_ACCOUNT_ID={wa_config.get('business_account_id', '')}",
                "",
            ])
        else:
            env_lines.extend([
                "# WhatsApp Configuration (configure in Admin Settings > WhatsApp tab)",
                f"WHATSAPP_PHONE_NUMBER_ID={os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')}",
                f"WHATSAPP_ACCESS_TOKEN={os.environ.get('WHATSAPP_ACCESS_TOKEN', '')}",
                f"WHATSAPP_BUSINESS_ACCOUNT_ID={os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '')}",
                "",
            ])
    except Exception:
        env_lines.extend([
            "# WhatsApp Configuration",
            f"WHATSAPP_PHONE_NUMBER_ID={os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')}",
            f"WHATSAPP_ACCESS_TOKEN={os.environ.get('WHATSAPP_ACCESS_TOKEN', '')}",
            f"WHATSAPP_BUSINESS_ACCOUNT_ID={os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '')}",
            "",
        ])
    
    # Payment Gateway settings (fallback)
    env_lines.extend([
        "# Payment Gateway Configuration (configure in Admin Settings > Payment Gateways tab)",
        f"RAZORPAY_KEY_ID={os.environ.get('RAZORPAY_KEY_ID', 'your_razorpay_key_id')}",
        f"RAZORPAY_KEY_SECRET={os.environ.get('RAZORPAY_KEY_SECRET', 'your_razorpay_key_secret')}",
        "",
    ])
    
    # Write .env file
    env_content = "\n".join(env_lines)
    root_env.write_text(env_content, encoding="utf-8")
    
    return str(root_env)


def generate_env_file(root_dir: Optional[Path] = None) -> str:
    """
    Synchronous wrapper for generating .env file.
    Use this if not in async context.
    
    Args:
        root_dir: Root directory for .env file. Defaults to workspace root.
    
    Returns:
        Path to generated .env file
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(generate_env_file_async(root_dir))