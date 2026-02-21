"""Configuration settings for AI Agent Service."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins() -> list[str]:
    """Parse CORS_ORIGINS environment variable."""
    cors_value = os.getenv("CORS_ORIGINS", '["http://localhost:5173", "http://localhost:8000"]')
    try:
        return json.loads(cors_value)
    except json.JSONDecodeError:
        return [cors_value.strip("[]").replace('"', "").replace("'", "")]


@dataclass(frozen=True, slots=True)
class AgentServiceSettings:
    """Settings for the AI Agent Service."""

    # Application
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "kobo-agent-service"))
    app_debug: bool = field(default_factory=lambda: os.getenv("APP_DEBUG", "false").lower() == "true")
    api_prefix: str = field(default_factory=lambda: os.getenv("API_PREFIX", "/api/v1"))
    cors_origins: list[str] = field(default_factory=_parse_cors_origins)

    # Ollama Configuration
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "openbmb/minicpm-o4.5:q4_K_M")
    )
    ollama_fallback_models: str = field(
        default_factory=lambda: os.getenv(
            "OLLAMA_FALLBACK_MODELS", "qwen3-vl:8b-instruct,qwen3:1.7b-q4_K_M"
        )
    )

    # Agent Configuration
    agent_default_temperature: float = field(
        default_factory=lambda: float(os.getenv("AGENT_DEFAULT_TEMPERATURE", "0.2"))
    )
    agent_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))
    )

    # Streaming Configuration
    enable_streaming: bool = field(
        default_factory=lambda: os.getenv("ENABLE_STREAMING", "true").lower() == "true"
    )


class Settings(BaseSettings):
    """Pydantic settings for validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "kobo-agent-service"
    app_debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=_parse_cors_origins)

    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "openbmb/minicpm-o4.5:q4_K_M"
    ollama_fallback_models: str = "qwen3-vl:8b-instruct,qwen3:1.7b-q4_K_M"

    # Agent
    agent_default_temperature: float = 0.2
    agent_timeout_seconds: int = 120
    enable_streaming: bool = True


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
