#!/bin/bash
# =============================================================================
# eBill — Container Health Watchdog
# =============================================================================
# Checks all Docker Compose services every 2 minutes via cron.
# Auto-restarts any container that is stopped or unhealthy.
#
# Install as cron (run 'make watchdog-install' or 'make setup-vps'):
#   */2 * * * * APP_DIR=/opt/ebill /opt/ebill/scripts/healthcheck.sh >> /var/log/ebill-watchdog.log 2>&1
#
# Manual run:
#   bash scripts/healthcheck.sh
# =============================================================================

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.ghcr.yml}"
LOG_FILE="/var/log/ebill-watchdog.log"
MAX_LOG_BYTES=102400   # 100KB — trim when exceeded

# ── Helpers ───────────────────────────────────────────────────────────────────
ts()  { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $1"; }

# Trim log file to stay below MAX_LOG_BYTES
if [ -f "$LOG_FILE" ] && [ "$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)" -gt "$MAX_LOG_BYTES" ]; then
    tail -c "$MAX_LOG_BYTES" "$LOG_FILE" > "${LOG_FILE}.tmp" 2>/dev/null && mv "${LOG_FILE}.tmp" "$LOG_FILE" 2>/dev/null || true
fi

# ── Check docker is available ─────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    log "ERROR: docker not found in PATH"
    exit 1
fi

# ── Change to app directory ───────────────────────────────────────────────────
if ! cd "$APP_DIR" 2>/dev/null; then
    log "ERROR: Cannot cd to APP_DIR=$APP_DIR"
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    log "ERROR: Compose file not found: $APP_DIR/$COMPOSE_FILE"
    exit 1
fi

# ── Check and restart a single service ───────────────────────────────────────
# Returns 0 if healthy, 1 if restarted or failed
check_service() {
    local svc="$1"

    # Get container ID from compose
    local cid
    cid=$(docker compose -f "$COMPOSE_FILE" ps -q "$svc" 2>/dev/null | head -1)

    if [ -z "$cid" ]; then
        log "WARN  $svc: not running — attempting start..."
        if docker compose -f "$COMPOSE_FILE" up -d "$svc" 2>&1 | grep -qiE 'error|failed'; then
            log "ERROR $svc: failed to start"
        else
            log "OK    $svc: started"
        fi
        return 1
    fi

    # Get current status
    local status health
    status=$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || echo "unknown")
    health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo "unknown")

    # Healthy states: running + (healthy or no healthcheck)
    if [ "$status" = "running" ] && { [ "$health" = "healthy" ] || [ "$health" = "none" ]; }; then
        return 0   # All good — no log noise on success
    fi

    # ── Unhealthy or not running — restart ─────────────────────────────────
    log "WARN  $svc: status=$status health=$health — restarting..."

    if docker compose -f "$COMPOSE_FILE" restart "$svc" 2>&1 | grep -qiE 'error|failed'; then
        log "ERROR $svc: restart failed"
        return 1
    fi

    # Brief wait then verify
    sleep 5
    local new_status
    new_status=$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || echo "unknown")
    if [ "$new_status" = "running" ]; then
        log "OK    $svc: restarted successfully (was $status)"
    else
        log "ERROR $svc: still not running after restart (status=$new_status)"
    fi
    return 1
}

# ── Memory pressure check ──────────────────────────────────────────────────────
check_memory() {
    local available_mb
    available_mb=$(free -m | awk '/^Mem:/{print $7}')
    local total_mb
    total_mb=$(free -m | awk '/^Mem:/{print $2}')
    local used_pct=$(( (total_mb - available_mb) * 100 / total_mb ))

    if [ "$used_pct" -gt 90 ]; then
        log "WARN  Memory pressure: ${used_pct}% used (${available_mb}MB free) — consider upgrading VPS"
    fi
}

# ── Main watchdog loop ────────────────────────────────────────────────────────
RESTARTED=0

for svc in mongodb backend frontend caddy; do
    check_service "$svc" || RESTARTED=$(( RESTARTED + 1 ))
done

# Only log memory summary when something was restarted or under pressure
check_memory

if [ "$RESTARTED" -gt 0 ]; then
    log "INFO  Watchdog cycle: $RESTARTED service(s) restarted"
fi
