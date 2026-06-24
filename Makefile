# JARVIS-LOCAL — developer commands
.DEFAULT_GOAL := help
SHELL := /bin/bash

BACKEND := backend
FRONTEND := frontend
PY := python3

.PHONY: help install backend frontend dev test eval lint \
        docker-up docker-down clean cli

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install backend (pip) and frontend (npm) dependencies
	cd $(BACKEND) && $(PY) -m pip install -r requirements.txt
	cd $(FRONTEND) && npm install

backend: ## Run the FastAPI backend (http://localhost:8000)
	cd $(BACKEND) && $(PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Run the Next.js dev server (http://localhost:3000)
	cd $(FRONTEND) && npm run dev

dev: ## Run backend and frontend together
	@echo "Starting backend + frontend… (Ctrl-C to stop)"
	@($(MAKE) backend &) ; $(MAKE) frontend

test: ## Run the backend test suite
	cd $(BACKEND) && $(PY) -m pytest -q

eval: ## Run the eval benchmark (Jarvis vs baseline)
	cd $(BACKEND) && $(PY) -m app.evals.runner run

cli: ## Show the CLI help
	cd $(BACKEND) && $(PY) -m app.cli.main --help

lint: ## Typecheck frontend + (optional) ruff backend
	cd $(FRONTEND) && npm run typecheck
	-cd $(BACKEND) && ruff check app || true

docker-up: ## Start the full stack with Docker Compose
	docker compose up --build -d

docker-down: ## Stop the Docker Compose stack
	docker compose down

clean: ## Remove caches and build artifacts (keeps your data dir)
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(BACKEND)/.pytest_cache $(FRONTEND)/.next
	@echo "cleaned."
