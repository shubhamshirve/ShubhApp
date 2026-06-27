# =============================================================================
# eBill — Deployment Makefile  (package manager: npm)
# Usage: make <target>
# =============================================================================

# Enable BuildKit for all Docker operations (faster builds, cache mounts)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export BUILDKIT_PROGRESS=plain

# Docker Compose file selector
COMPOSE_FILE ?= docker-compose.prod.yml
DC = docker compose -f $(COMPOSE_FILE)

# GHCR config
GHCR_USER     ?= shubhamshirve
GHCR_REGISTRY  = ghcr.io
IMAGE_PREFIX   = $(GHCR_REGISTRY)/$(GHCR_USER)/shubhapp

# Colours
GREEN  = \033[0;32m
YELLOW = \033[0;33m
CYAN   = \033[0;36m
NC     = \033[0m

.PHONY: help build up down restart logs deploy deploy-ghcr pull pull-images \
        pull-ghcr ghcr-login watchtower-up watchtower-down watchtower-logs \
        rollback-ghcr clean backup status shell-backend shell-frontend

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-22s$(NC) %s\n", $$1, $$2}'

# ── GHCR Authentication ───────────────────────────────────────────────────────
ghcr-login: ## Login to GHCR — requires: export CR_PAT=ghp_your_token
	@test -n "$(CR_PAT)" || (echo "$(YELLOW)Error: CR_PAT not set$(NC)" && \
	  echo "Run: export CR_PAT=ghp_your_token  (read:packages scope)" && exit 1)
	@echo "$(CYAN)Logging in to $(GHCR_REGISTRY)...$(NC)"
	@echo "$(CR_PAT)" | docker login $(GHCR_REGISTRY) -u $(GHCR_USER) --password-stdin
	@echo "$(GREEN)GHCR login successful. Watchtower will use these credentials.$(NC)"

# ── GHCR Pull images ─────────────────────────────────────────────────────────
pull-images: ## Pull latest images from GHCR (no restart)
	@echo "$(CYAN)Pulling latest GHCR images...$(NC)"
	docker pull $(IMAGE_PREFIX)-backend:latest
	docker pull $(IMAGE_PREFIX)-frontend:latest
	@echo "$(GREEN)Images pulled.$(NC)"

# ── GHCR Deploy (Option B — manual) ─────────────────────────────────────────
deploy-ghcr: pull pull-images ## Pull latest code + GHCR images + restart (no build on VPS)
	@echo "$(CYAN)Starting services with GHCR images...$(NC)"
	docker compose -f docker-compose.ghcr.yml up -d --no-build --remove-orphans
	docker image prune -f
	@echo "$(GREEN)GHCR deployment complete!$(NC)"

pull-ghcr: deploy-ghcr ## Alias for deploy-ghcr

# ── Watchtower (Option C — auto-deploy) ──────────────────────────────────────
watchtower-up: ## Start Watchtower (auto-pulls GHCR images every 5 min)
	@echo "$(CYAN)Starting Watchtower...$(NC)"
	@echo "$(YELLOW)Note: Run 'make ghcr-login' first if using private GHCR packages.$(NC)"
	docker compose -f docker-compose.ghcr.yml up -d watchtower
	@echo "$(GREEN)Watchtower running. Polls GHCR every 5 minutes.$(NC)"

watchtower-down: ## Stop Watchtower
	@echo "$(YELLOW)Stopping Watchtower...$(NC)"
	docker compose -f docker-compose.ghcr.yml stop watchtower
	docker compose -f docker-compose.ghcr.yml rm -f watchtower

watchtower-logs: ## Tail Watchtower logs
	docker compose -f docker-compose.ghcr.yml logs -f --tail=50 watchtower

# ── Rollback ─────────────────────────────────────────────────────────────────
rollback-ghcr: ## Rollback to a specific image tag — usage: make rollback-ghcr TAG=abc1234
	@test -n "$(TAG)" || (echo "$(YELLOW)Usage: make rollback-ghcr TAG=<git-sha>$(NC)" && exit 1)
	@echo "$(YELLOW)Rolling back to tag: $(TAG)$(NC)"
	docker pull $(IMAGE_PREFIX)-backend:$(TAG)
	docker pull $(IMAGE_PREFIX)-frontend:$(TAG)
	docker tag $(IMAGE_PREFIX)-backend:$(TAG) $(IMAGE_PREFIX)-backend:latest
	docker tag $(IMAGE_PREFIX)-frontend:$(TAG) $(IMAGE_PREFIX)-frontend:latest
	docker compose -f docker-compose.ghcr.yml up -d --no-build --remove-orphans
	@echo "$(GREEN)Rollback to $(TAG) complete!$(NC)"

# ── Build (local / staging only — NOT for 1GB VPS) ───────────────────────────
build: ## Build all images locally (not for 1GB RAM VPS — use deploy-ghcr instead)
	@echo "$(YELLOW)Warning: Building locally. Use deploy-ghcr for 1GB VPS.$(NC)"
	$(DC) build --parallel

build-no-cache: ## Force-rebuild all images without cache
	$(DC) build --no-cache --parallel

build-backend: ## Rebuild backend image only
	$(DC) build backend

build-frontend: ## Rebuild frontend image only
	$(DC) build frontend

# ── Service lifecycle ─────────────────────────────────────────────────────────
up: ## Start all services (uses COMPOSE_FILE, default: docker-compose.prod.yml)
	@echo "$(GREEN)Starting services...$(NC)"
	$(DC) up -d

down: ## Stop and remove containers
	@echo "$(YELLOW)Stopping services...$(NC)"
	$(DC) down

restart: ## Restart all services
	$(DC) restart

restart-backend: ## Restart backend only
	$(DC) restart backend

restart-frontend: ## Restart frontend only
	$(DC) restart frontend

status: ## Show service status
	docker compose -f docker-compose.ghcr.yml ps

# ── Logs ──────────────────────────────────────────────────────────────────────
logs: ## Tail all service logs
	docker compose -f docker-compose.ghcr.yml logs -f --tail=100

logs-backend: ## Tail backend logs
	docker compose -f docker-compose.ghcr.yml logs -f --tail=100 backend

logs-frontend: ## Tail frontend logs
	docker compose -f docker-compose.ghcr.yml logs -f --tail=100 frontend

logs-mongo: ## Tail MongoDB logs
	docker compose -f docker-compose.ghcr.yml logs -f --tail=50 mongodb

# ── Git Pull ──────────────────────────────────────────────────────────────────
pull: ## Pull latest code from live branch
	git pull origin live

# ── Legacy deploy (keep for compatibility) ────────────────────────────────────
deploy: pull deploy-ghcr ## Full deploy: pull code + pull GHCR images + restart

# ── Backup ────────────────────────────────────────────────────────────────────
backup: ## Trigger a manual backup via API
	@echo "$(YELLOW)Creating backup...$(NC)"
	@BACKEND_URL=$$(grep REACT_APP_BACKEND_URL .env 2>/dev/null | cut -d= -f2 | sed 's|/api||'); \
	  curl -s -X POST "$${BACKEND_URL:-http://localhost:8000}/api/admin/backup/create" \
	    -H "Content-Type: application/json" | python3 -m json.tool

# ── Shells ────────────────────────────────────────────────────────────────────
shell-backend: ## Open a shell in the backend container
	docker compose -f docker-compose.ghcr.yml exec backend bash

shell-frontend: ## Open a shell in the frontend container
	docker compose -f docker-compose.ghcr.yml exec frontend sh

shell-mongo: ## Open MongoDB shell
	docker compose -f docker-compose.ghcr.yml exec mongodb mongosh

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Stop services and remove orphan containers
	docker compose -f docker-compose.ghcr.yml down --remove-orphans

clean-all: ## Remove containers, images, volumes (DESTRUCTIVE)
	@echo "$(YELLOW)WARNING: This will delete all data. Press Ctrl+C to cancel...$(NC)"
	@sleep 5
	docker compose -f docker-compose.ghcr.yml down --volumes --rmi local --remove-orphans

prune-images: ## Remove dangling Docker images
	docker image prune -f

prune-build-cache: ## Clear Docker build cache
	docker builder prune -f
