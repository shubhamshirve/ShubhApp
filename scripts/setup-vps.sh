#!/bin/bash
# =============================================================================
# eBill — VPS Initial Setup
# =============================================================================
# Run ONCE on a fresh VPS as root. Safe to re-run (idempotent).
#
# What this does:
#   1. Creates 2GB swap file (critical safety net for RAM spikes)
#   2. Sets vm.swappiness=10 (use swap only when RAM is almost full)
#   3. Calculates percentage-based memory limits (auto-config)
#   4. Installs health watchdog as a cron job (every 2 minutes)
#
# Usage:
#   sudo bash scripts/setup-vps.sh
#   make setup-vps         (runs with sudo automatically)
# =============================================================================

set -euo pipefail

# Colours
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
info() { echo "  $1"; }

echo ""
echo "=== eBill VPS Setup ==="
echo ""

# ── Root check ─────────────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (or with sudo)${NC}"
    echo "  Usage: sudo bash scripts/setup-vps.sh"
    exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
WATCHDOG_SCRIPT="$APP_DIR/scripts/healthcheck.sh"

# ── Step 1: Swap space ─────────────────────────────────────────────────────────
echo "[1/4] Swap Space"

SWAP_TOTAL=$(free -m | awk '/^Swap:/{print $2}')
SWAP_SIZE_GB=2

if [ "$SWAP_TOTAL" -lt 512 ]; then
    info "No swap detected — creating ${SWAP_SIZE_GB}GB swap file at /swapfile..."

    # Create swap file (fallocate is faster; dd is fallback)
    if command -v fallocate &>/dev/null; then
        fallocate -l "${SWAP_SIZE_GB}G" /swapfile
    else
        dd if=/dev/zero of=/swapfile bs=1M count=$(( SWAP_SIZE_GB * 1024 )) status=progress
    fi

    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile

    # Persist swap across reboots
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
        info "Added /swapfile to /etc/fstab (persists across reboots)"
    fi

    ok "Swap created: ${SWAP_SIZE_GB}GB"
else
    ok "Swap already present: ${SWAP_TOTAL}MB (skipping)"
fi

# ── Step 2: Kernel memory settings ────────────────────────────────────────────
echo ""
echo "[2/4] Kernel Memory Tuning"

# swappiness=10: only use swap when RAM is 90%+ full (not aggressively)
CURRENT_SWAPPINESS=$(cat /proc/sys/vm/swappiness)
if [ "$CURRENT_SWAPPINESS" -ne 10 ]; then
    sysctl -w vm.swappiness=10 > /dev/null
    # Persist across reboots
    if ! grep -q 'vm.swappiness' /etc/sysctl.conf; then
        echo 'vm.swappiness=10' >> /etc/sysctl.conf
    else
        sed -i 's/vm.swappiness=.*/vm.swappiness=10/' /etc/sysctl.conf
    fi
    ok "vm.swappiness set to 10 (was $CURRENT_SWAPPINESS)"
else
    ok "vm.swappiness already at 10"
fi

# overcommit: prevent OOM on small VPS
sysctl -w vm.overcommit_memory=1 > /dev/null 2>&1 || true
if ! grep -q 'vm.overcommit_memory' /etc/sysctl.conf; then
    echo 'vm.overcommit_memory=1' >> /etc/sysctl.conf
fi
ok "vm.overcommit_memory set to 1"

# ── Step 3: Docker daemon — MTU + DNS fix ─────────────────────────────────────
echo ""
echo "[3/5] Docker Daemon Configuration"

DAEMON_JSON="/etc/docker/daemon.json"
if [ ! -f "$DAEMON_JSON" ] || ! grep -q '"mtu"' "$DAEMON_JSON"; then
    info "Configuring Docker daemon (MTU=1450, DNS=8.8.8.8)..."
    info "This fixes TLS handshake timeouts when pulling images on VPS networks."
    cat > "$DAEMON_JSON" << 'DOCKERCFG'
{
  "dns": ["8.8.8.8", "8.8.4.4"],
  "mtu": 1450,
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
DOCKERCFG
    systemctl restart docker
    sleep 5
    ok "Docker daemon configured and restarted"
else
    ok "Docker daemon already configured (skipping)"
fi

# ── Step 4: Auto memory configuration ─────────────────────────────────────────
echo ""
echo "[4/5] Memory Limits Configuration"
bash "$APP_DIR/scripts/auto-config.sh"

# ── Step 5: Health watchdog cron ──────────────────────────────────────────────
echo "[5/5] Health Watchdog"

chmod +x "$WATCHDOG_SCRIPT"

CRON_JOB="*/2 * * * * APP_DIR=$APP_DIR $WATCHDOG_SCRIPT >> /var/log/ebill-watchdog.log 2>&1"

# Remove old entry (if any) and add fresh one
( crontab -l 2>/dev/null | grep -v 'healthcheck.sh' ; echo "$CRON_JOB" ) | crontab -

# Create log file with correct permissions
touch /var/log/ebill-watchdog.log
chmod 644 /var/log/ebill-watchdog.log

ok "Watchdog installed — runs every 2 minutes"
info "Logs: tail -f /var/log/ebill-watchdog.log"

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo "=== Setup Complete ==="
SWAP_NOW=$(free -h | awk '/^Swap:/{print $2}')
RAM_NOW=$(free -h | awk '/^Mem:/{print $2}')
info "Total RAM:    $RAM_NOW"
info "Swap:         $SWAP_NOW"
info "Watchdog:     every 2 minutes (cron)"
echo ""
echo "Next steps:"
info "1. Ensure .env has all required variables (DOMAIN, MONGO credentials, etc.)"
info "2. make ghcr-login  — login to GHCR (if images are private)"
info "3. make deploy-ghcr — pull images and start all services"
echo ""
