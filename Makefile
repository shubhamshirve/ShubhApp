# =============================================================================
# eBill — Makefile
# Usage: make <target>
# =============================================================================

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

DC  = docker compose -f docker-compose.prod.yml
DCG = docker compose -f docker-compose.ghcr.yml

GREEN  = \033[0;32m
YELLOW = \033[0;33m
RED    = \033[0;31m
NC     = \033[0m

.PHONY: help deploy pull build up down restart logs status backup \
        shell-backend shell-frontend shell-mongo clean clean-all prune-images \
        auto-config setup-vps watchdog-install watchdog-remove watchdog-logs health \
        ghcr-login deploy-ghcr pull-images watchtower-up watchtower-down rollback-ghcr

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-22s$(NC) %s\n", $$1, $$2}'

# ── 1GB RAM Optimization ──────────────────────────────────────────────────────
auto-config: ## Detect RAM and write % memory limits to .env (re-run after VPS upgrade)
	@bash ./scripts/auto-config.sh

setup-vps: ## Full VPS setup: swap + kernel tuning + auto-config + watchdog (run as root)
	@sudo bash ./scripts/setup-vps.sh

watchdog-install: ## Install health watchdog as cron job (auto-restarts crashed services every 2min)
	@chmod +x ./scripts/healthcheck.sh
	@SCRIPT_PATH="$$(realpath ./scripts/healthcheck.sh)"; \
	 APP_PATH="$$(realpath .)"; \
	 CRON_JOB="*/2 * * * * APP_DIR=$$APP_PATH $$SCRIPT_PATH >> /var/log/ebill-watchdog.log 2>&1"; \
	 ( crontab -l 2>/dev/null | grep -v 'healthcheck.sh' ; echo "$$CRON_JOB" ) | crontab -
	@echo "$(GREEN)✓ Watchdog installed — checks every 2 minutes$(NC)"
	@echo "  Logs: make watchdog-logs"

watchdog-remove: ## Remove health watchdog from cron
	@crontab -l 2>/dev/null | grep -v 'healthcheck.sh' | crontab - || true
	@echo "$(GREEN)✓ Watchdog removed$(NC)"

watchdog-logs: ## Tail health watchdog logs
	@tail -f /var/log/ebill-watchdog.log

health: ## Show current health status of all services
	@echo "$(GREEN)=== Service Health ===$(NC)"
	@$(DCG) ps 2>/dev/null || $(DC) ps
	@echo ""
	@echo "$(GREEN)=== Memory Usage ===$(NC)"
	@free -h
	@echo ""
	@echo "$(GREEN)=== Container Memory ===$(NC)"
	@docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}" 2>/dev/null || true

# ── GHCR Deploy (production with pre-built images) ────────────────────────────
ghcr-login: ## Login to GHCR — set CR_PAT and GITHUB_USER env vars first
	@[ -n "$${CR_PAT}" ] || (echo "$(RED)Error: set CR_PAT=ghp_... before running$(NC)" && exit 1)
	@echo "$${CR_PAT}" | docker login ghcr.io -u "$${GITHUB_USER:-shubhamshirve}" --password-stdin
	@echo "$(GREEN)✓ Logged in to GHCR$(NC)"

deploy-ghcr: ## Pull latest GHCR images and restart services
	@echo "$(GREEN)Pulling GHCR images...$(NC)"
	$(DCG) pull
	$(DCG) up -d --remove-orphans
	docker image prune -f
	@echo "$(GREEN)✓ GHCR deployment complete$(NC)"

pull-images: ## Pull latest images from GHCR without restarting
	$(DCG) pull

watchtower-up: ## Start Watchtower (auto-updates containers when new image pushed)
	$(DCG) up -d watchtower
	@echo "$(GREEN)✓ Watchtower started (polls every 5 min)$(NC)"

watchtower-down: ## Stop Watchtower
	$(DCG) stop watchtower && $(DCG) rm -f watchtower
	@echo "$(GREEN)✓ Watchtower stopped$(NC)"

rollback-ghcr: ## Rollback to a specific image tag (usage: make rollback-ghcr TAG=abc1234)
	@[ -n "$(TAG)" ] || (echo "$(RED)Usage: make rollback-ghcr TAG=abc1234$(NC)" && exit 1)
	@echo "$(YELLOW)Rolling back to tag: $(TAG)$(NC)"
	@VERSION=$(TAG) $(DCG) up -d --no-build backend frontend
	@echo "$(GREEN)✓ Rolled back to $(TAG)$(NC)"

# ── Deploy (build-based) ──────────────────────────────────────────────────────
deploy: pull ## Pull latest code and rebuild + restart all services
	@echo "$(GREEN)Building and starting services...$(NC)"
	$(DC) up -d --build --remove-orphans
	docker image prune -f
	@echo "$(GREEN)Deployment complete!$(NC)"

pull: ## Pull latest code from live branch
	git pull origin live

# ── Build ─────────────────────────────────────────────────────────────────────
build: ## Build all images
	$(DC) build --parallel

build-no-cache: ## Force-rebuild all images without cache
	$(DC) build --no-cache --parallel

# ── Service lifecycle ─────────────────────────────────────────────────────────
up: ## Start all services
	$(DC) up -d

down: ## Stop and remove containers
	$(DC) down

restart: ## Restart all services
	$(DC) restart

restart-backend: ## Restart backend only
	$(DC) restart backend

restart-frontend: ## Restart frontend only
	$(DC) restart frontend

status: ## Show service status
	$(DC) ps

# ── Logs ──────────────────────────────────────────────────────────────────────
logs: ## Tail all service logs
	$(DC) logs -f --tail=100

logs-backend: ## Tail backend logs
	$(DC) logs -f --tail=100 backend

logs-frontend: ## Tail frontend logs
	$(DC) logs -f --tail=100 frontend

logs-mongo: ## Tail MongoDB logs
	$(DC) logs -f --tail=50 mongodb

# ── Backup ────────────────────────────────────────────────────────────────────
backup: ## Trigger a manual backup via API
	@BACKEND_URL=$$(grep REACT_APP_BACKEND_URL .env 2>/dev/null | cut -d= -f2); \
	  curl -s -X POST "$${BACKEND_URL:-http://localhost:8000}/api/admin/backup/create" \
	    -H "Content-Type: application/json" | python3 -m json.tool

# ── Shells ────────────────────────────────────────────────────────────────────
shell-backend: ## Open a shell in the backend container
	$(DC) exec backend bash

shell-frontend: ## Open a shell in the frontend container
	$(DC) exec frontend sh

shell-mongo: ## Open MongoDB shell
	$(DC) exec mongodb mongosh

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Stop services and remove orphan containers
	$(DC) down --remove-orphans

clean-all: ## Remove containers, images, volumes (DESTRUCTIVE)
	@echo "$(YELLOW)WARNING: This will delete all data. Press Ctrl+C to cancel...$(NC)"
	@sleep 5
	$(DC) down --volumes --rmi local --remove-orphans

prune-images: ## Remove dangling Docker images
	docker image prune -f
