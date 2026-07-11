#!/usr/bin/env bash
# =============================================================================
# eBill — VPS Bootstrap for Option B (GitHub Actions + Docker Hub CI/CD)
# =============================================================================
# Run this ONCE on a fresh VPS before setting up GitHub Actions.
# After this script runs, every `git push origin live` will auto-deploy.
#
# Usage:  sudo bash vps-bootstrap-optionb.sh
#
# What it does:
#   1. Installs Docker, Docker Compose plugin, git, make
#   2. Clones the repo
#   3. Creates the .env file with all required values
#   4. Generates SSH key pair for GitHub Actions to use
#   5. Prints all GitHub Secrets you need to set
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

banner() { echo -e "\n${BLUE}══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${BLUE}══════════════════════════════════════════════════${NC}\n"; }
info()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()   { echo -e "${YELLOW}[!]${NC} $1"; }
error()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step()   { echo -e "${BOLD}${BLUE}──── $1${NC}"; }
ask()    { echo -e "${YELLOW}[?]${NC} $1"; }

[[ $EUID -ne 0 ]] && error "Run as root: sudo bash vps-bootstrap-optionb.sh"

banner "eBill — VPS Bootstrap (Option B)"
echo "  Sets up this VPS to receive automated deploys from GitHub Actions."
echo "  Run this ONCE, then add the printed secrets to your GitHub repo."
echo ""

# =============================================================================
# STEP 1 — Install dependencies
# =============================================================================
banner "Step 1 — Installing Docker & Tools"

apt-get update -qq
apt-get install -y -qq curl git make openssl ca-certificates gnupg lsb-release

if ! command -v docker &>/dev/null; then
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
  info "Docker installed"
else
  info "Docker already installed: $(docker --version)"
fi

docker compose version &>/dev/null || error "Docker Compose plugin missing."
info "Docker Compose: $(docker compose version --short)"

# =============================================================================
# STEP 2 — Clone / locate repo
# =============================================================================
banner "Step 2 — Repository"

DEFAULT_PATH="/root/ShubhApp"
ask "Deploy path on this VPS? [${DEFAULT_PATH}]"
read -r DEPLOY_PATH
DEPLOY_PATH="${DEPLOY_PATH:-$DEFAULT_PATH}"

if [ -d "$DEPLOY_PATH/.git" ]; then
  info "Repo already exists at $DEPLOY_PATH"
  cd "$DEPLOY_PATH"
else
  DEFAULT_REPO="https://github.com/shubhamshirve/ShubhApp.git"
  ask "GitHub repo URL? [${DEFAULT_REPO}]"
  read -r REPO_URL
  REPO_URL="${REPO_URL:-$DEFAULT_REPO}"
  mkdir -p "$DEPLOY_PATH"
  git clone "$REPO_URL" "$DEPLOY_PATH"
  cd "$DEPLOY_PATH"
  git checkout live 2>/dev/null || git checkout main 2>/dev/null || true
  info "Repo cloned to $DEPLOY_PATH"
fi

cd "$DEPLOY_PATH"
mkdir -p dbbackups
info "dbbackups/ directory ready"

# =============================================================================
# STEP 3 — Collect environment values
# =============================================================================
banner "Step 3 — Environment Configuration"
echo "  Values with [brackets] are defaults — press Enter to accept."
echo ""

# Domain
ask "Your domain (e.g. app.yourdomain.com):"
read -r DOMAIN
while [[ -z "$DOMAIN" ]]; do
  warn "Domain is required!"
  ask "Your domain:"
  read -r DOMAIN
done

# Server IP
DETECTED_IP=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')
ask "VPS public IP? [${DETECTED_IP}]"
read -r SERVER_IP
SERVER_IP="${SERVER_IP:-$DETECTED_IP}"

# Backend URL
DEFAULT_BACKEND_URL="https://${DOMAIN}"
ask "REACT_APP_BACKEND_URL? [${DEFAULT_BACKEND_URL}]"
read -r REACT_APP_BACKEND_URL
REACT_APP_BACKEND_URL="${REACT_APP_BACKEND_URL:-$DEFAULT_BACKEND_URL}"

# CORS
ask "CORS_ORIGINS (comma-separated)? [https://${DOMAIN}]"
read -r CORS_ORIGINS
CORS_ORIGINS="${CORS_ORIGINS:-https://${DOMAIN}}"

# Docker Hub username (required for image pull)
ask "Docker Hub username (images will be pulled as <user>/ebill-backend:latest):"
read -r DOCKER_USERNAME
while [[ -z "$DOCKER_USERNAME" ]]; do
  warn "Docker Hub username is required!"
  ask "Docker Hub username:"
  read -r DOCKER_USERNAME
done

# MongoDB
ask "MongoDB admin username? [ebilladmin]"
read -r MONGO_ROOT_USERNAME
MONGO_ROOT_USERNAME="${MONGO_ROOT_USERNAME:-ebilladmin}"

ask "MongoDB admin password (blank = auto-generate):"
read -rs MONGO_ROOT_PASSWORD; echo ""
if [[ -z "$MONGO_ROOT_PASSWORD" ]]; then
  MONGO_ROOT_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
  info "MongoDB password auto-generated"
fi

ask "Database name? [saas_db]"
read -r DB_NAME
DB_NAME="${DB_NAME:-saas_db}"

ask "JWT secret (blank = auto-generate 64-char):"
read -rs JWT_SECRET; echo ""
if [[ -z "$JWT_SECRET" ]]; then
  JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n' | head -c 64)
  info "JWT secret auto-generated"
fi

ask "Backup encryption password (blank = auto-generate):"
read -rs BACKUP_PASSWORD; echo ""
if [[ -z "$BACKUP_PASSWORD" ]]; then
  BACKUP_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
  info "Backup password auto-generated"
fi

# =============================================================================
# STEP 4 — Write .env.production
# =============================================================================
banner "Step 4 — Writing .env.production"

ENV_FILE="$DEPLOY_PATH/.env.production"
[ -f "$ENV_FILE" ] && cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)" && warn "Backed up old .env.production"

cat > "$ENV_FILE" << ENVEOF
# eBill Production Environment — generated by vps-bootstrap-optionb.sh on $(date)

# ── Network ─────────────────────────────────────────────────────────────────
DOMAIN=${DOMAIN}
SERVER_IP=${SERVER_IP}

# ── Docker Hub (image names in docker-compose.prod.yml) ──────────────────────
DOCKER_USERNAME=${DOCKER_USERNAME}

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
ENVEOF

chmod 600 "$ENV_FILE"
info ".env.production written (permissions 600)"

# Also write a plain .env symlink so the deploy script can find it
ln -sf ".env.production" "$DEPLOY_PATH/.env" 2>/dev/null || cp "$ENV_FILE" "$DEPLOY_PATH/.env"
chmod 600 "$DEPLOY_PATH/.env"

# =============================================================================
# STEP 5 — Update Caddyfile domain
# =============================================================================
banner "Step 5 — Caddyfile"

CADDYFILE="$DEPLOY_PATH/Caddyfile"
if [ -f "$CADDYFILE" ]; then
  sed -i "1s|.*|${DOMAIN} {|" "$CADDYFILE"
  info "Caddyfile updated: first line → ${DOMAIN} {"
else
  warn "Caddyfile not found — skipping"
fi

# =============================================================================
# STEP 6 — Generate SSH key pair for GitHub Actions
# =============================================================================
banner "Step 6 — SSH Key for GitHub Actions"

KEY_FILE="/root/.ssh/github_actions_deploy"
if [ -f "$KEY_FILE" ]; then
  warn "SSH key already exists at $KEY_FILE — using existing key"
else
  ssh-keygen -t ed25519 -C "github-actions-deploy" -f "$KEY_FILE" -N ""
  info "SSH key generated: $KEY_FILE"
fi

# Add public key to authorized_keys
PUBLIC_KEY=$(cat "${KEY_FILE}.pub")
mkdir -p /root/.ssh
if grep -qF "$PUBLIC_KEY" /root/.ssh/authorized_keys 2>/dev/null; then
  info "Public key already in authorized_keys"
else
  echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys
  chmod 600 /root/.ssh/authorized_keys
  info "Public key added to /root/.ssh/authorized_keys"
fi

# =============================================================================
# STEP 7 — Save credentials & print GitHub Secrets
# =============================================================================
banner "Step 7 — GitHub Secrets You Must Add"

CREDS_FILE="$DEPLOY_PATH/.vps-credentials.txt"
PRIVATE_KEY=$(cat "$KEY_FILE")

cat > "$CREDS_FILE" << CREDSEOF
eBill VPS Bootstrap Credentials — $(date)
==========================================
Deploy Path:            ${DEPLOY_PATH}
Domain:                 ${DOMAIN}
URL:                    https://${DOMAIN}
Server IP:              ${SERVER_IP}

Docker Hub Username:    ${DOCKER_USERNAME}
MongoDB User:           ${MONGO_ROOT_USERNAME}
MongoDB Password:       ${MONGO_ROOT_PASSWORD}
Database:               ${DB_NAME}
JWT Secret:             ${JWT_SECRET}
Backup Password:        ${BACKUP_PASSWORD}

SSH Private Key File:   ${KEY_FILE}
SSH Public Key:         ${KEY_FILE}.pub
CREDSEOF
chmod 600 "$CREDS_FILE"

# Print the secrets table
echo -e "${BOLD}Add these 8 secrets to your GitHub repo:${NC}"
echo -e "${CYAN}  Repo → Settings → Secrets and variables → Actions → New repository secret${NC}"
echo ""
echo -e "${YELLOW}┌────────────────────────────┬────────────────────────────────────────────────────────┐${NC}"
printf "${YELLOW}│${NC} %-26s ${YELLOW}│${NC} %-54s ${YELLOW}│${NC}\n" "Secret name" "Value"
echo -e "${YELLOW}├────────────────────────────┼────────────────────────────────────────────────────────┤${NC}"
printf "${YELLOW}│${NC} %-26s ${YELLOW}│${NC} %-54s ${YELLOW}│${NC}\n" "DOCKER_USERNAME"    "$DOCKER_USERNAME"
printf "${YELLOW}│${NC} %-26s ${YELLOW}│${NC} %-54s ${YELLOW}│${NC}\n" "DOCKER_PASSWORD"    "<your Docker Hub password or access token>"
printf "${YELLOW}│${NC} %-26s ${YELLOW}│${NC} %-54s ${YELLOW}│${NC}\n" "PROD_SERVER_IP"     "$SERVER_IP"
printf "${YELLOW}│${NC} %-26s ${YELLOW}│${NC} %-54s ${YELLOW}│${NC}\n" "SERVER_USER"        "root"
printf "${YELLOW}│${NC} %-26s ${YELLOW}│${NC} %-54s ${YELLOW}│${NC}\n" "DEPLOY_KEY"         "<see below — full private key content>"
printf "${YELLOW}│${NC} %-26s ${YELLOW}│${NC} %-54s ${YELLOW}│${NC}\n" "DEPLOY_PATH"        "$DEPLOY_PATH"
printf "${YELLOW}│${NC} %-26s ${YELLOW}│${NC} %-54s ${YELLOW}│${NC}\n" "DEPLOY_PORT"        "22"
printf "${YELLOW}│${NC} %-26s ${YELLOW}│${NC} %-54s ${YELLOW}│${NC}\n" "REACT_APP_BACKEND_URL" "$REACT_APP_BACKEND_URL"
echo -e "${YELLOW}└────────────────────────────┴────────────────────────────────────────────────────────┘${NC}"
echo ""
echo -e "${BOLD}DEPLOY_KEY value (copy everything including the BEGIN/END lines):${NC}"
echo -e "${CYAN}─────────────────────────────────────────────────────────────────${NC}"
cat "$KEY_FILE"
echo -e "${CYAN}─────────────────────────────────────────────────────────────────${NC}"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  VPS bootstrap complete!                                      ║${NC}"
echo -e "${GREEN}║                                                               ║${NC}"
echo -e "${GREEN}║  Next steps:                                                  ║${NC}"
echo -e "${GREEN}║  1. Add the 8 secrets above to GitHub                         ║${NC}"
echo -e "${GREEN}║  2. Create a Docker Hub account if you don't have one         ║${NC}"
echo -e "${GREEN}║     → https://hub.docker.com                                  ║${NC}"
echo -e "${GREEN}║  3. Point DNS: ${DOMAIN} → ${SERVER_IP}   ║${NC}"
echo -e "${GREEN}║  4. git push origin live → auto-deploys!                      ║${NC}"
echo -e "${GREEN}║                                                               ║${NC}"
echo -e "${GREEN}║  Credentials saved to: .vps-credentials.txt                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
