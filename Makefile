# =============================================================================
# eBill — Makefile
# Usage: make <target>
# =============================================================================

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

DC      = docker compose -f docker-compose.prod.yml
DC_GHCR = docker compose -f docker-compose.ghcr.yml

GREEN  = \033[0;32m
YELLOW = \033[0;33m
NC     = \033[0m

.PHONY: help deploy deploy-ghcr pull pull-images build up down restart logs status backup \
        shell-backend shell-frontend shell-mongo clean clean-all prune-images \
        watchtower-up watchtower-down rollback-ghcr ghcr-login

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-22s$(NC) %s\n", $$1, $$2}'

# ── Deploy ────────────────────────────────────────────────────────────────────
deploy: pull ## Pull latest code and rebuild + restart all services (builds on VPS)
	@echo "$(GREEN)Building and starting services...$(NC)"
	mkdir -p dbbackups
	$(DC) up -d --build --remove-orphans
	docker image prune -f
	@echo "$(GREEN)Deployment complete!$(NC)"

deploy-ghcr: pull-images ## Pull latest pre-built images and restart without building on VPS
	@echo "$(GREEN)Deploying pre-built images...$(NC)"
	mkdir -p dbbackups
	$(DC_GHCR) down --remove-orphans
	$(DC_GHCR) up -d --remove-orphans
	docker image prune -f
	@echo "$(GREEN)Deployment complete!$(NC)"

pull: ## Pull latest code from live branch
	git pull origin live

pull-images: ## Pull latest pre-built images from GHCR/Docker Hub (no build)
	@echo "$(YELLOW)Pulling latest images...$(NC)"
	$(DC_GHCR) pull

ghcr-login: ## Login to GHCR (set CR_PAT and GHCR_USER env vars first)
	@echo "$(YELLOW)Logging in to GHCR...$(NC)"
	@echo "$${CR_PAT}" | docker login ghcr.io -u "$${GHCR_USER:-shubhamshirve}" --password-stdin

rollback-ghcr: ## Rollback to a specific image tag: make rollback-ghcr TAG=abc1234
	@[ -n "$(TAG)" ] || (echo "Usage: make rollback-ghcr TAG=<git-sha>"; exit 1)
	@echo "$(YELLOW)Rolling back to tag $(TAG)...$(NC)"
	VERSION=$(TAG) $(DC_GHCR) pull
	VERSION=$(TAG) $(DC_GHCR) down --remove-orphans
	VERSION=$(TAG) $(DC_GHCR) up -d --remove-orphans
	@echo "$(GREEN)Rollback to $(TAG) complete!$(NC)"

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

# ── Watchtower ────────────────────────────────────────────────────────────────
watchtower-up: ## Start Watchtower for auto-deploy on new GHCR images
	$(DC_GHCR) up -d watchtower

watchtower-down: ## Stop Watchtower
	$(DC_GHCR) rm -sf watchtower

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
