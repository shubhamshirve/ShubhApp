#!/usr/bin/env bash
# =============================================================================
# eBill — Fresh VPS Setup Script
# =============================================================================
# Supports: Ubuntu 20.04 / 22.04 / 24.04 (and most Debian-based systems)
# Run as root or with sudo:   sudo bash vps-setup.sh
#
# What this script does:
#   1. Installs Docker, Docker Compose plugin, git, make, curl
#   2. Clones or updates the repo on the VPS
#   3. Interactively collects all required environment variables
#   4. Creates the .env file
#   5. Updates the Caddyfile with your domain
#   6. Builds and starts all services
#   7. Prints access information
# =============================================================================

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

banner() { echo -e "\n${BLUE}═══════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"; }
info()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()   { echo -e "${YELLOW}[!]${NC} $1"; }
error()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
prompt() { echo -e "${YELLOW}[?]${NC} $1"; }

# ── Root check ────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  error "Please run as root: sudo bash vps-setup.sh"
fi

banner "eBill — VPS Setup"
echo "  This script will install all dependencies and start eBill."
echo "  Estimated time: 5–15 minutes (depends on server speed)."
echo ""

# ── OS check ──────────────────────────────────────────────────────────────────
if [ -f /etc/os-release ]; then
  . /etc/os-release
  OS=$NAME
  VER=$VERSION_ID
  info "Detected OS: $OS $VER"
else
  warn "Cannot detect OS — proceeding anyway (Ubuntu/Debian expected)"
  OS="Unknown"
fi

# ── Step 1: Install system dependencies ───────────────────────────────────────
banner "Step 1 — Installing System Dependencies"

apt-get update -qq

# Install basic tools
apt-get install -y -qq curl git make openssl ca-certificates gnupg lsb-release jq
info "Basic tools installed (curl, git, make, openssl)"

# ── Install Docker if not present ─────────────────────────────────────────────
if command -v docker &>/dev/null; then
  DOCKER_VER=$(docker --version)
  info "Docker already installed: $DOCKER_VER"
else
  info "Installing Docker..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable docker --now
  info "Docker installed successfully"
fi

# Verify docker compose v2
if docker compose version &>/dev/null; then
  info "Docker Compose plugin available: $(docker compose version --short)"
else
  error "Docker Compose plugin not found. Please install docker-compose-plugin manually."
fi

# ── Step 2: Get repo ───────────────────────────────────────────────────────────
banner "Step 2 — Repository Setup"

DEFAULT_DEPLOY_PATH="/opt/ebill"
prompt "Where should eBill be installed? [${DEFAULT_DEPLOY_PATH}]"
read -r DEPLOY_PATH
DEPLOY_PATH="${DEPLOY_PATH:-$DEFAULT_DEPLOY_PATH}"

if [ -d "$DEPLOY_PATH/.git" ]; then
  info "Repo already exists at $DEPLOY_PATH"
  prompt "Pull latest changes? (y/n) [y]"
  read -r PULL_LATEST
  if [[ "${PULL_LATEST:-y}" =~ ^[Yy]$ ]]; then
    cd "$DEPLOY_PATH"
    git pull origin live 2>/dev/null || git pull origin main 2>/dev/null || warn "Could not pull — continuing with current code"
  fi
else
  DEFAULT_REPO="https://github.com/shubhamshirve/ShubhApp.git"
  prompt "GitHub repo URL? [${DEFAULT_REPO}]"
  read -r REPO_URL
  REPO_URL="${REPO_URL:-$DEFAULT_REPO}"

  mkdir -p "$DEPLOY_PATH"
  info "Cloning $REPO_URL → $DEPLOY_PATH ..."
  git clone "$REPO_URL" "$DEPLOY_PATH"
  cd "$DEPLOY_PATH"
  git checkout live 2>/dev/null || true
  info "Repo cloned successfully"
fi

cd "$DEPLOY_PATH"

# ── Step 3: Collect environment variables ─────────────────────────────────────
banner "Step 3 — Environment Configuration"

echo "  Please provide the following configuration values."
echo "  Press Enter to accept defaults shown in [brackets]."
echo ""

# ── DOMAIN ────────────────────────────────────────────────────────────────────
prompt "Your domain name (e.g. app.yourdomain.com) — required for HTTPS:"
read -r DOMAIN
while [[ -z "$DOMAIN" ]]; do
  warn "Domain is required for SSL/HTTPS!"
  prompt "Your domain name (e.g. app.yourdomain.com):"
  read -r DOMAIN
done

# ── SERVER_IP ─────────────────────────────────────────────────────────────────
SERVER_IP=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || \
            curl -s --max-time 5 https://ifconfig.me 2>/dev/null || \
            hostname -I 2>/dev/null | awk '{print $1}')
prompt "VPS public IP address? [${SERVER_IP}]"
read -r INPUT_IP
SERVER_IP="${INPUT_IP:-$SERVER_IP}"

# ── REACT_APP_BACKEND_URL ─────────────────────────────────────────────────────
DEFAULT_BACKEND_URL="https://${DOMAIN}"
prompt "Full backend URL (with https) ? [${DEFAULT_BACKEND_URL}]"
read -r REACT_APP_BACKEND_URL
REACT_APP_BACKEND_URL="${REACT_APP_BACKEND_URL:-$DEFAULT_BACKEND_URL}"

# ── CORS_ORIGINS ──────────────────────────────────────────────────────────────
DEFAULT_CORS="https://${DOMAIN}"
prompt "CORS allowed origins (comma-separated) ? [${DEFAULT_CORS}]"
read -r CORS_ORIGINS
CORS_ORIGINS="${CORS_ORIGINS:-$DEFAULT_CORS}"

# ── MongoDB credentials ────────────────────────────────────────────────────────
prompt "MongoDB admin username ? [ebilladmin]"
read -r MONGO_ROOT_USERNAME
MONGO_ROOT_USERNAME="${MONGO_ROOT_USERNAME:-ebilladmin}"

prompt "MongoDB admin password (leave blank to auto-generate):"
read -rs MONGO_ROOT_PASSWORD
echo ""
if [[ -z "$MONGO_ROOT_PASSWORD" ]]; then
  MONGO_ROOT_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
  info "MongoDB password auto-generated"
fi

# ── DB_NAME ───────────────────────────────────────────────────────────────────
prompt "Database name ? [saas_db]"
read -r DB_NAME
DB_NAME="${DB_NAME:-saas_db}"

# ── JWT_SECRET ────────────────────────────────────────────────────────────────
prompt "JWT secret (leave blank to auto-generate 64-char secret):"
read -rs JWT_SECRET
echo ""
if [[ -z "$JWT_SECRET" ]]; then
  JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n' | head -c 64)
  info "JWT secret auto-generated"
fi

# ── BACKUP_PASSWORD ───────────────────────────────────────────────────────────
prompt "Backup encryption password (leave blank to auto-generate):"
read -rs BACKUP_PASSWORD
echo ""
if [[ -z "$BACKUP_PASSWORD" ]]; then
  BACKUP_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
  info "Backup password auto-generated"
fi

# ── Step 4: Write .env file ───────────────────────────────────────────────────
banner "Step 4 — Writing .env File"

ENV_FILE="$DEPLOY_PATH/.env"

# Back up existing .env if present
if [ -f "$ENV_FILE" ]; then
  cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
  warn "Backed up existing .env to ${ENV_FILE}.bak.*"
fi

cat > "$ENV_FILE" << EOF
# eBill Production Environment — generated by vps-setup.sh on $(date)

# ── Network ───────────────────────────────────────────────────────────────────
DOMAIN=${DOMAIN}
SERVER_IP=${SERVER_IP}

# ── Frontend / CORS ──────────────────────────────────────────────────────────
REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}
CORS_ORIGINS=${CORS_ORIGINS}

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_ROOT_USERNAME=${MONGO_ROOT_USERNAME}
MONGO_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD}
DB_NAME=${DB_NAME}

# ── Security ──────────────────────────────────────────────────────────────────
JWT_SECRET=${JWT_SECRET}
BACKUP_PASSWORD=${BACKUP_PASSWORD}
EOF

chmod 600 "$ENV_FILE"
info ".env written to $ENV_FILE (permissions: 600)"

# ── Step 5: Update Caddyfile ──────────────────────────────────────────────────
banner "Step 5 — Updating Caddyfile"

CADDYFILE="$DEPLOY_PATH/Caddyfile"
if [ -f "$CADDYFILE" ]; then
  # Replace the first line (the domain) with the new domain
  OLD_DOMAIN=$(head -1 "$CADDYFILE" | tr -d '{' | tr -d ' ')
  sed -i "1s|.*|${DOMAIN} {|" "$CADDYFILE"
  info "Caddyfile domain updated: $OLD_DOMAIN → $DOMAIN"
else
  warn "Caddyfile not found at $CADDYFILE — skipping"
fi

# ── Step 6: Create required directories ──────────────────────────────────────
banner "Step 6 — Preparing Directories"

mkdir -p "$DEPLOY_PATH/dbbackups"
info "Created dbbackups/ directory"

# ── Step 7: Build and start ───────────────────────────────────────────────────
banner "Step 7 — Building & Starting Services"

echo ""
echo "  This step builds Docker images on this VPS and starts all services."
echo "  It may take 5–10 minutes on first run."
echo ""
prompt "Start deployment now? (y/n) [y]"
read -r START_NOW
if [[ "${START_NOW:-y}" =~ ^[Nn]$ ]]; then
  warn "Skipping deployment. Run manually later: cd $DEPLOY_PATH && make deploy"
  exit 0
fi

cd "$DEPLOY_PATH"

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

info "Running: docker compose -f docker-compose.prod.yml up -d --build"
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

info "Pruning unused images..."
docker image prune -f

# ── Step 8: Post-startup checks ────────────────────────────────────────────────
banner "Step 8 — Health Check"

echo "  Waiting 30 seconds for services to become healthy..."
sleep 30

docker compose -f docker-compose.prod.yml ps

# Check if backend is up
if curl -sf "http://localhost:8000/api/health" &>/dev/null; then
  info "Backend health check: PASSED"
else
  warn "Backend not yet responding. Check logs: make logs-backend"
fi

# ── Summary ────────────────────────────────────────────────────────────────────
banner "Setup Complete!"

CREDS_FILE="$DEPLOY_PATH/.vps-credentials.txt"
cat > "$CREDS_FILE" << EOF
eBill Deployment Credentials — $(date)
========================================
Domain:             ${DOMAIN}
URL:                https://${DOMAIN}
Server IP:          ${SERVER_IP}

MongoDB User:       ${MONGO_ROOT_USERNAME}
MongoDB Password:   ${MONGO_ROOT_PASSWORD}
Database Name:      ${DB_NAME}

JWT Secret:         ${JWT_SECRET}
Backup Password:    ${BACKUP_PASSWORD}
EOF
chmod 600 "$CREDS_FILE"

echo -e "${GREEN}"
echo "  ┌─────────────────────────────────────────────────────┐"
echo "  │  eBill is running!                                  │"
echo "  │                                                     │"
echo -e "  │  URL:    ${CYAN}https://${DOMAIN}${GREEN}"
echo "  │                                                     │"
echo "  │  Next steps:                                        │"
echo "  │  1. Point DNS → ${SERVER_IP}                        │"
echo "  │     (add an A record: ${DOMAIN} → ${SERVER_IP})     │"
echo "  │  2. Caddy auto-issues SSL once DNS propagates       │"
echo "  │  3. Create your admin account via the app           │"
echo "  │                                                     │"
echo "  │  Credentials saved to: .vps-credentials.txt        │"
echo "  │  (keep this file safe and back it up)               │"
echo "  └─────────────────────────────────────────────────────┘"
echo -e "${NC}"

echo ""
echo -e "${YELLOW}Useful commands (run from $DEPLOY_PATH):${NC}"
echo ""
printf "  %-30s %s\n" "make status"       "→ Show container status"
printf "  %-30s %s\n" "make logs"         "→ Tail all logs"
printf "  %-30s %s\n" "make logs-backend" "→ Backend logs only"
printf "  %-30s %s\n" "make restart"      "→ Restart all services"
printf "  %-30s %s\n" "make backup"       "→ Manual DB backup"
printf "  %-30s %s\n" "make down"         "→ Stop all services"
printf "  %-30s %s\n" "make deploy"       "→ Pull latest code & rebuild"
echo ""
