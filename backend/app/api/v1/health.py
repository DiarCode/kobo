from __future__ import annotations

import socket
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter

from app.core.config import get_settings
from app.domain.schemas import HealthDependency, HealthOut

router = APIRouter(tags=["health"])


def _tcp_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_host_port(url_or_host: str, default_port: int) -> tuple[str, int]:
    if "://" in url_or_host:
        parsed = urlparse(url_or_host)
        host = parsed.hostname or "localhost"
        port = parsed.port or default_port
        return host, port
    if ":" in url_or_host:
        host, _, port_raw = url_or_host.rpartition(":")
        try:
            return host, int(port_raw)
        except ValueError:
            return url_or_host, default_port
    return url_or_host, default_port


def _http_reachable(url: str, *, endpoint: str = "") -> bool:
    target = f"{url.rstrip('/')}{endpoint}"
    parsed = urlparse(target)
    verify_tls = parsed.scheme == "https"
    try:
        response = httpx.get(target, timeout=1.5, follow_redirects=True, verify=verify_tls)
        return response.status_code < 500
    except httpx.HTTPError:
        return False


def _dep(status_ok: bool, detail: str) -> HealthDependency:
    return HealthDependency(status="ok" if status_ok else "degraded", detail=detail)


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    settings = get_settings()
    postgres_host, postgres_port = _parse_host_port(settings.database_url, 5432)
    redis_host, redis_port = _parse_host_port(settings.redis_url, 6379)
    neo4j_host, neo4j_port = _parse_host_port(settings.neo4j_url, 7687)
    temporal_host, temporal_port = _parse_host_port(settings.temporal_host, 7233)

    livekit_http_url = settings.livekit_url
    if livekit_http_url.startswith("wss://"):
        livekit_http_url = "https://" + livekit_http_url.removeprefix("wss://")
    elif livekit_http_url.startswith("ws://"):
        livekit_http_url = "http://" + livekit_http_url.removeprefix("ws://")

    deps = {
        "postgres": _dep(_tcp_reachable(postgres_host, postgres_port), settings.database_url),
        "redis": _dep(_tcp_reachable(redis_host, redis_port), settings.redis_url),
        "qdrant": _dep(_http_reachable(settings.qdrant_url), settings.qdrant_url),
        "neo4j": _dep(_tcp_reachable(neo4j_host, neo4j_port), settings.neo4j_url),
        "elasticsearch": _dep(_http_reachable(settings.elasticsearch_url), settings.elasticsearch_url),
        "temporal": _dep(_tcp_reachable(temporal_host, temporal_port), settings.temporal_host),
        "ollama": _dep(_http_reachable(settings.ollama_base_url, endpoint="/api/tags"), settings.ollama_base_url),
        "livekit": _dep(_http_reachable(livekit_http_url), settings.livekit_url),
    }
    return HealthOut(service=settings.app_name, environment=settings.app_env, version="0.1.0", dependencies=deps)
