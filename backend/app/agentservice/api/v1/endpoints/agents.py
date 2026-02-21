"""Agent execution endpoints with streaming support."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from app.agentservice.core.config import get_settings
from app.agentservice.services.agent_runtime import AgentRuntime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()
agent_runtime = AgentRuntime()


class AgentRunRequest(BaseModel):
    """Request model for agent execution."""

    role_key: str
    goal: str
    workspace_id: str
    task_id: str | None = None
    temperature: float | None = None
    stream: bool = False


class AgentRunResponse(BaseModel):
    """Response model for agent execution."""

    executive_summary: str
    full_content: str
    grounded_claims: list[dict[str, Any]]
    assumptions: list[dict[str, Any]]
    confidence_score: float
    confidence_breakdown: dict[str, float]
    open_questions: list[str]
    review_flags: list[str]
    model_used: str | None = None


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    """Run an agent with the given role and goal."""
    try:
        temperature = request.temperature or settings.agent_default_temperature
        result = await agent_runtime.run(
            role_key=request.role_key,
            goal=request.goal,
            workspace_id=request.workspace_id,
            task_id=request.task_id,
            temperature=temperature,
        )
        return AgentRunResponse(
            executive_summary=result.executive_summary,
            full_content=result.full_content,
            grounded_claims=[claim.model_dump() for claim in result.grounded_claims],
            assumptions=[assump.model_dump() for assump in result.assumptions],
            confidence_score=result.confidence_score,
            confidence_breakdown=result.confidence_breakdown,
            open_questions=result.open_questions,
            review_flags=result.review_flags,
            model_used=getattr(result, "model_used", None),
        )
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/stream")
async def run_agent_stream(request: AgentRunRequest):
    """Run an agent with streaming response using Server-Sent Events."""
    from fastapi.responses import StreamingResponse

    async def generate():
        """Generate streaming response."""
        try:
            yield f"data: {json.dumps({'type': 'start', 'role_key': request.role_key})}\n\n"

            temperature = request.temperature or settings.agent_default_temperature
            result = await agent_runtime.run(
                role_key=request.role_key,
                goal=request.goal,
                workspace_id=request.workspace_id,
                task_id=request.task_id,
                temperature=temperature,
            )

            # Stream the content in chunks
            content = result.full_content
            chunk_size = 50  # characters per chunk
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.02)  # Small delay for visual effect

            # Send final result
            yield f"data: {json.dumps({'type': 'complete', 'result': result.model_dump()})}\n\n"

        except Exception as e:
            logger.error(f"Agent streaming failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/models")
async def list_models():
    """List available Ollama models."""
    try:
        url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            models = [model.get("name", "") for model in data.get("models", [])]
            return {"models": models}
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        # Return configured models as fallback
        fallback_models = [settings.ollama_model] + [
            m.strip() for m in settings.ollama_fallback_models.split(",")
        ]
        return {"models": fallback_models, "note": "Ollama unavailable, returning configured models"}
