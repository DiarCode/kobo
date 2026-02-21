# KOBO

KOBO is an autonomous execution workspace where humans and AI role-agents coordinate tasks, artifacts, approvals, and decision logs across a shared Work Graph.

## Stack

- Frontend: Vue + TanStack Query + KY + Tailwind + shadcn-compatible UI + Phaser Office Mode
- Backend: FastAPI + uv + Prisma schema/client + event bus/orchestrator services
- Local infra: Docker Compose with Postgres/pgvector, Redis, Qdrant, Neo4j, Elasticsearch, MinIO, Temporal, pgAdmin
- Local model: Ollama at `http://192.168.8.104:11434` with `openbmb/minicpm-o4.5:q4_K_M`

## Run

```bash
# create env files once
make env

# one-time bootstrap (deps + prisma client + prisma db push)
make bootstrap

# run full project (backend + worker + frontend + infra)
make up

# watch logs
make logs

# stop everything
make down
```

### Local split mode (without compose)

```bash
make env
make install

# terminal 1
make backend-run

# terminal 2
make frontend-dev
```

## Validation

```bash
make check
```
