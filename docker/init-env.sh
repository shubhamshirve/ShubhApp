#!/bin/sh
set -eu

ROOT_DIR="/workspace"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

mkdir -p "$BACKEND_DIR" "$FRONTEND_DIR"

if [ ! -f "$ROOT_DIR/.env" ]; then
  cat > "$ROOT_DIR/.env" <<'EOF'
DOMAIN=localhost
SERVER_IP=
MONGO_URI=mongodb://mongodb:27017/saas_db
CORS_ORIGINS=https://localhost,http://localhost
REACT_APP_BACKEND_URL=
MONGO_URL=mongodb://localhost:27017/saas_db
DB_NAME=saas_db
JWT_SECRET=change-this-to-a-strong-random-secret
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_BUSINESS_ACCOUNT_ID=
BACKUP_PASSWORD=change-this-backup-password
EOF
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  cat > "$BACKEND_DIR/.env" <<'EOF'
MONGO_URL=mongodb://localhost:27017/saas_db
DB_NAME=saas_db
CORS_ORIGINS=http://localhost:3000
JWT_SECRET=change-this-to-a-strong-random-secret
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_BUSINESS_ACCOUNT_ID=
BACKUP_PASSWORD=change-this-backup-password
EOF
fi

if [ ! -f "$FRONTEND_DIR/.env.local" ]; then
  cat > "$FRONTEND_DIR/.env.local" <<'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
EOF
fi
