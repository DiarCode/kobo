SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose
BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: help env backend-install backend-run backend-test backend-lint backend-typecheck db-up prisma-generate prisma-push frontend-install frontend-dev frontend-lint frontend-test frontend-typecheck frontend-build frontend-e2e install bootstrap up down restart logs ps health check-backend check-frontend check

help:
	@echo "KOBO Make targets"
	@echo "  make install          - install backend/frontend dependencies"
	@echo "  make env              - create .env files from .env.example when missing"
	@echo "  make bootstrap        - env + install + prisma generate + prisma db push"
	@echo "  make up               - start full stack via docker compose"
	@echo "  make down             - stop full stack"
	@echo "  make logs             - stream docker compose logs"
	@echo "  make ps               - show docker compose services"
	@echo "  make health           - check backend health endpoint"
	@echo "  make check            - run backend and frontend quality gates"

env:
	@test -f .env || cp .env.example .env
	@test -f $(BACKEND_DIR)/.env || cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env
	@test -f $(FRONTEND_DIR)/.env || cp $(FRONTEND_DIR)/.env.example $(FRONTEND_DIR)/.env

backend-install:
	cd $(BACKEND_DIR) && uv sync --all-groups

backend-run:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-test:
	cd $(BACKEND_DIR) && uv run pytest

backend-lint:
	cd $(BACKEND_DIR) && uv run ruff check .

backend-typecheck:
	cd $(BACKEND_DIR) && uv run mypy app

db-up:
	$(COMPOSE) up -d postgres-pgvector

prisma-generate:
	cd $(BACKEND_DIR) && uv run prisma generate --schema prisma/schema.prisma

prisma-push: db-up
	cd $(BACKEND_DIR) && uv run prisma db push --schema prisma/schema.prisma

frontend-install:
	cd $(FRONTEND_DIR) && bun install

frontend-dev:
	cd $(FRONTEND_DIR) && bun run dev

frontend-lint:
	cd $(FRONTEND_DIR) && bun lint

frontend-test:
	cd $(FRONTEND_DIR) && bun test:unit

frontend-typecheck:
	cd $(FRONTEND_DIR) && bun run type-check

frontend-build:
	cd $(FRONTEND_DIR) && bun run build

frontend-e2e:
	cd $(FRONTEND_DIR) && CI=1 bun test:e2e --project=chromium

install: backend-install frontend-install

bootstrap: env install prisma-generate prisma-push

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart: down up

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

health:
	@for i in $$(seq 1 30); do \
		if curl -sf http://localhost:8000/api/v1/health; then \
			echo ""; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "Backend is not healthy"; \
	exit 1

check-backend: backend-lint backend-typecheck backend-test

check-frontend: frontend-lint frontend-typecheck frontend-test frontend-build frontend-e2e

check: check-backend check-frontend
