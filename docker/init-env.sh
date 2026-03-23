#!/bin/sh
set -eu

ROOT_DIR="/workspace"

if [ ! -f "$ROOT_DIR/.env" ]; then
  cat > "$ROOT_DIR/.env" <<'EOF'
DOMAIN=app.e-bill.in
SERVER_IP=45.196.196.21
MONGO_URI=mongodb://mongodb:27017/saas_db
CORS_ORIGINS=https://localhost,http://localhost
REACT_APP_BACKEND_URL=
MONGO_URL=mongodb://localhost:27017/saas_db
DB_NAME=saas_db
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=shubhamhirve
MONGO_BIND_ADDRESS=127.0.0.1
JWT_SECRET=shubhamhirve
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RESEND_API_KEY=
RESEND_FROM_EMAIL=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_BUSINESS_ACCOUNT_ID=
BACKUP_PASSWORD=shubhamhirve
EOF
fi
