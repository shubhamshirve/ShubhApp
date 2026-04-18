"""Application configuration constants."""
import os
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# Environment Detection
# ============================================================================
ENV = os.environ.get('ENV', 'development').lower()
IS_PRODUCTION = ENV == 'production'
IS_DEVELOPMENT = ENV == 'development'

# ============================================================================
# Security Configuration (Required)
# ============================================================================
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    if IS_PRODUCTION:
        raise ValueError("JWT_SECRET is required in production!")
    JWT_SECRET = 'dev-key-change-in-production-2024'
    logger.warning("JWT_SECRET not set — using insecure development fallback. Set JWT_SECRET in production.")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

BACKUP_PASSWORD = os.environ.get('BACKUP_PASSWORD')
if not BACKUP_PASSWORD:
    if IS_PRODUCTION:
        raise ValueError("BACKUP_PASSWORD is required in production!")
    BACKUP_PASSWORD = 'dev-password'
    logger.warning("BACKUP_PASSWORD not set — using insecure development fallback. Set BACKUP_PASSWORD in production.")

# ============================================================================
# Database Configuration
# ============================================================================
DB_NAME = os.environ.get('DB_NAME', 'saas_db')
MONGO_URI = os.environ.get('MONGO_URI')

# Fallback: build from components if MONGO_URI not set
if not MONGO_URI:
    MONGO_HOST = os.environ.get('MONGO_HOST', 'mongodb' if not IS_DEVELOPMENT else 'localhost')
    MONGO_PORT = os.environ.get('MONGO_PORT', '27017')
    MONGO_USERNAME = os.environ.get('MONGO_ROOT_USERNAME', 'admin')
    MONGO_PASSWORD = os.environ.get('MONGO_ROOT_PASSWORD')
    MONGO_AUTH_DB = os.environ.get('MONGO_AUTH_DB', 'admin')
    
    if MONGO_USERNAME and MONGO_PASSWORD:
        from urllib.parse import quote_plus
        MONGO_URI = (
            f"mongodb://{quote_plus(MONGO_USERNAME)}:{quote_plus(MONGO_PASSWORD)}"
            f"@{MONGO_HOST}:{MONGO_PORT}/{DB_NAME}?authSource={quote_plus(MONGO_AUTH_DB)}"
        )
    else:
        MONGO_URI = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{DB_NAME}"

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG' if IS_DEVELOPMENT else 'INFO')
ENABLE_QUERY_LOGGING = IS_DEVELOPMENT  # Log all DB queries in dev only
ENABLE_DETAILED_ERRORS = IS_DEVELOPMENT  # Show full tracebacks in dev

# ============================================================================
# CORS Configuration
# ============================================================================
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8000')
CORS_ORIGINS_LIST = [origin.strip() for origin in CORS_ORIGINS.split(',') if origin.strip()]

# ============================================================================
# API Configuration
# ============================================================================
API_TITLE = "eBill - Multi-Tenant SaaS Billing Platform"
API_VERSION = os.environ.get('APP_VERSION', '1.0.0')
API_DESCRIPTION = "REST API for billing, invoicing, and payment management"
API_DOCS_ENABLED = IS_DEVELOPMENT  # Disable /docs in production

# ============================================================================
# Performance & Security Settings
# ============================================================================
class Environment(str, Enum):
    """Environment enumeration."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    STAGING = "staging"

# Request size limits
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_JSON_SIZE = 10 * 1024 * 1024    # 10 MB

# Rate limiting
RATE_LIMIT_ENABLED = IS_PRODUCTION  # Only in production
RATE_LIMIT_REQUESTS_PER_MINUTE = 60

# ============================================================================
# WhatsApp WebJS Service Configuration
# ============================================================================
WHATSAPP_WEBJS_URL = os.environ.get('WHATSAPP_WEBJS_URL', 'http://localhost:8002')

# ============================================================================
# Feature Flags (can be overridden per environment)
# ============================================================================
FEATURES = {
    "email_enabled": bool(os.environ.get('RESEND_API_KEY') or os.environ.get('SMTP_HOST')),
    "whatsapp_enabled": bool(os.environ.get('WHATSAPP_ACCESS_TOKEN')),
    "razorpay_enabled": bool(os.environ.get('RAZORPAY_KEY_ID')),
    "scheduler_enabled": True,
    "audit_logging_enabled": True,
    "api_docs_enabled": API_DOCS_ENABLED,
}
