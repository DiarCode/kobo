"""API v1 router for AI Agent Service."""

from __future__ import annotations

from app.agentservice.api.v1.endpoints import agents, chat, health
from fastapi import APIRouter

api_router = APIRouter()

# Include endpoints
api_router.include_router(health.router, tags=["health"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
