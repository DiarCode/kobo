# KOBO Makefile Guide

## Prerequisites

- Docker + Docker Compose
- `uv`
- `bun`

## First-time setup

```bash
make env
make bootstrap
```

What this does:
- creates missing `.env` files from examples
- installs backend/frontend dependencies
- generates Prisma client
- syncs Prisma schema to DB

## Run full project

```bash
make up
```

Services and default URLs:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/v1
- Backend health: http://localhost:8000/api/v1/health
- pgAdmin: http://localhost:5050
- MinIO console: http://localhost:9001
- Temporal UI: http://localhost:8233
- Neo4j browser: http://localhost:7474

## Operate stack

```bash
make ps      # list running services
make logs    # stream service logs
make health  # check backend health endpoint
make restart # restart full stack
make down    # stop full stack
```

## Quality checks

```bash
make check
```

Runs:
- backend lint + typecheck + tests
- frontend lint + typecheck + unit + build + e2e

## Useful partial commands

```bash
make backend-run
make frontend-dev
make backend-test
make frontend-test
```
