#!/bin/sh
set -eu

ROOT_DIR="${1:-.}"

# Minimal .env generation for Docker
# SECURITY NOTE: Only core variables here. Credentials are set via environment variables or admin UI.
# All settings (Email, WhatsApp, Payment) are now managed in Admin Settings UI.

if [ ! -f "$ROOT_DIR/.env" ]; then
  cat > "$ROOT_DIR/.env" <<EOF
# Core Network Configuration
DOMAIN=${DOMAIN:-localhost}
SERVER_IP=${SERVER_IP:-}

# MongoDB Configuration (required for all environments)
MONGO_URI=${MONGO_URI:-mongodb://mongodb:27017/saas_db}
MONGO_ROOT_USERNAME=${MONGO_ROOT_USERNAME:-admin}
MONGO_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD:-}
DB_NAME=${DB_NAME:-saas_db}

# API Configuration (required)
CORS_ORIGINS=${CORS_ORIGINS:-}
REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL:-}

# Security Credentials (REQUIRED - Set in production!)
JWT_SECRET=${JWT_SECRET:-}
BACKUP_PASSWORD=${BACKUP_PASSWORD:-}

# Optional integrations - now managed in Admin Settings
# Leave empty if not using:
# - Payment settings (Razorpay)
# - Email settings (Resend/SMTP)
# - WhatsApp configuration
EOF
fi
