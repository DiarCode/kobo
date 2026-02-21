"""AI Agent Service - Main FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from app.agentservice.api.router import router as api_router
from app.agentservice.core.config import get_settings
from app.agentservice.core.logging import configure_logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

settings = get_settings()
configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    logger.info("AI Agent Service starting up...")
    yield
    logger.info("AI Agent Service shutting down...")


app = FastAPI(
    title="KOBO AI Agent Service",
    description="Microservice for AI agent execution and LLM operations",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "service": "ai-agent-service",
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.agentservice.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.app_debug,
    )
