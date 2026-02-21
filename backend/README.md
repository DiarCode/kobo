# KOBO Backend

FastAPI + uv + Prisma schema backend for KOBO autonomous execution workspace.

## Quickstart

```bash
uv sync --all-groups
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Prisma

```bash
uv run prisma generate --schema prisma/schema.prisma
uv run prisma db push --schema prisma/schema.prisma
```
