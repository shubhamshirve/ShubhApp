# =============================================================================
# eBill — Deployment Makefile
# Usage: make <target>
# =============================================================================

# Enable BuildKit for all Docker operations (faster builds, cache mounts)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export BUILDKIT_PROGRESS=plain

# Docker Compose file selector
COMPOSE_FILE ?= docker-compose.prod.yml
DC = docker compose -f $(COMPOSE_FILE)

# Colours
GREEN  = \033[0;32m
YELLOW = \033[0;33m
NC     = \033[0m

.PHONY: help build up down restart logs deploy clean pull backup status shell-backend shell-frontend

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ── Build ─────────────────────────────────────────────────────────────────────
build: ## Build all images (uses BuildKit cache)
	@echo "$(YELLOW)Building images...$(NC)"
	$(DC) build --parallel

build-no-cache: ## Force-rebuild all images without cache
	@echo "$(YELLOW)Rebuilding all images from scratch...$(NC)"
	$(DC) build --no-cache --parallel

build-backend: ## Rebuild backend image only
	$(DC) build backend

build-frontend: ## Rebuild frontend image only
	$(DC) build frontend

# ── Service lifecycle ─────────────────────────────────────────────────────────
up: ## Start all services in detached mode
	@echo "$(GREEN)Starting services...$(NC)"
	$(DC) up -d

down: ## Stop and remove containers
	@echo "$(YELLOW)Stopping services...$(NC)"
	$(DC) down

restart: ## Restart all services
	$(DC) restart

restart-backend: ## Restart backend service only
	$(DC) restart backend

restart-frontend: ## Restart frontend service only
	$(DC) restart frontend

status: ## Show service status
	$(DC) ps

# ── Logs ──────────────────────────────────────────────────────────────────────
logs: ## Tail logs from all services
	$(DC) logs -f --tail=100

logs-backend: ## Tail backend logs
	$(DC) logs -f --tail=100 backend

logs-frontend: ## Tail frontend logs
	$(DC) logs -f --tail=100 frontend

logs-mongo: ## Tail MongoDB logs
	$(DC) logs -f --tail=50 mongodb

# ── Deploy ────────────────────────────────────────────────────────────────────
deploy: pull build up ## Full deploy: pull latest code, build images, start services
	@echo "$(GREEN)Deployment complete!$(NC)"

pull: ## Pull latest code from git
	git pull origin main

rollback: ## Roll back to previous Docker image
	@echo "$(YELLOW)Rolling back services...$(NC)"
	$(DC) down
	docker image ls --format '{{.Repository}}:{{.Tag}}' | grep ebill | head -5
	@echo "Run: docker tag <old-image> <current-image> then make up"

# ── Backup ────────────────────────────────────────────────────────────────────
backup: ## Trigger a manual backup via API
	@echo "$(YELLOW)Creating backup...$(NC)"
	@BACKEND_URL=$$(grep REACT_APP_BACKEND_URL .env 2>/dev/null | cut -d= -f2 | sed 's|/api||'); \
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
clean: down ## Stop services and remove orphan containers
	$(DC) down --remove-orphans

clean-all: down ## Remove containers, images, volumes (DESTRUCTIVE)
	@echo "$(YELLOW)WARNING: This will delete all data. Press Ctrl+C to cancel..."
	@sleep 5
	$(DC) down --volumes --rmi local --remove-orphans

prune-images: ## Remove dangling Docker images
	docker image prune -f

prune-build-cache: ## Clear Docker build cache
	docker builder prune -f
