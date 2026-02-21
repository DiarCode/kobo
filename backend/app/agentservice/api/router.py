"""API router for AI Agent Service."""

from __future__ import annotations

from app.agentservice.api.v1.router import api_router as v1_router
from fastapi import APIRouter

router = APIRouter()

# Include v1 API routes
router.include_router(v1_router, prefix="/v1")
