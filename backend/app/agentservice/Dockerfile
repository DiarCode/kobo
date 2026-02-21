FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --all-groups --no-install-project

COPY . .
RUN uv sync --all-groups

EXPOSE 8001

CMD ["uv", "run", "uvicorn", "app.agentservice.main:app", "--host", "0.0.0.0", "--port", "8001"]
