from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "KOBO Backend"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    frontend_base_url: str = "http://localhost:5173"

    database_url: str = "postgresql://kobo:kobo@localhost:5432/kobo"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    neo4j_url: str = "bolt://localhost:7687"
    elasticsearch_url: str = "http://localhost:9200"
    temporal_host: str = "localhost:7233"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_bucket: str = "kobo-files"
    minio_secure: bool = False
    minio_public_base_url: str = "http://localhost:9000"

    # AI Agent Service
    agent_service_url: str = "http://localhost:8001/api/v1"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 7
    access_cookie_name: str = "kobo_access_token"
    refresh_cookie_name: str = "kobo_refresh_token"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None

    ollama_base_url: str = "http://192.168.8.104:11434"
    ollama_model: str = "openbmb/minicpm-o4.5:q4_K_M"
    ollama_fallback_models: str = "qwen3-vl:8b-instruct,qwen3:1.7b-q4_K_M"
    ollama_embeddings_model: str = "nomic-embed-text"
    livekit_url: str = "ws://livekit:7880"
    livekit_public_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/github/callback"

    linear_client_id: str = ""
    linear_client_secret: str = ""
    linear_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/linear/callback"

    feature_council_mode: bool = True
    feature_office_mode: bool = True
    feature_external_actions: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
