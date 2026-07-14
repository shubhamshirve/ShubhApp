#!/bin/sh

ROOT_DIR="${1:-.}"

# Minimal .env generation for Docker
# SECURITY NOTE: Only core variables here. Credentials are set via environment variables or admin UI.

ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "# Core Network Configuration" > "$ENV_FILE"
  echo "DOMAIN=${DOMAIN:-localhost}" >> "$ENV_FILE"
  echo "SERVER_IP=${SERVER_IP:-}" >> "$ENV_FILE"
  echo "" >> "$ENV_FILE"
  echo "# MongoDB Configuration (required for all environments)" >> "$ENV_FILE"
  echo "MONGO_URI=${MONGO_URI:-mongodb://mongodb:27017/ebill_db}" >> "$ENV_FILE"
  echo "MONGO_ROOT_USERNAME=${MONGO_ROOT_USERNAME:-admin}" >> "$ENV_FILE"
  echo "MONGO_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD:-}" >> "$ENV_FILE"
  echo "DB_NAME=${DB_NAME:-ebill_db}" >> "$ENV_FILE"
  echo "" >> "$ENV_FILE"
  echo "# API Configuration (required)" >> "$ENV_FILE"
  echo "CORS_ORIGINS=${CORS_ORIGINS:-}" >> "$ENV_FILE"
  echo "REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL:-}" >> "$ENV_FILE"
  echo "" >> "$ENV_FILE"
  echo "# Security Credentials (REQUIRED - Set in production!)" >> "$ENV_FILE"
  echo "JWT_SECRET=${JWT_SECRET:-}" >> "$ENV_FILE"
  echo "BACKUP_PASSWORD=${BACKUP_PASSWORD:-}" >> "$ENV_FILE"
fi

exit 0
