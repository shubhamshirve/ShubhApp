# =============================================================================
# eBill — Makefile
# Usage: make <target>
# =============================================================================

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

DC = docker compose -f docker-compose.prod.yml

GREEN  = \033[0;32m
YELLOW = \033[0;33m
NC     = \033[0m

.PHONY: help deploy pull build up down restart logs status backup \
        shell-backend shell-frontend shell-mongo clean clean-all prune-images

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ── Deploy ────────────────────────────────────────────────────────────────────
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
