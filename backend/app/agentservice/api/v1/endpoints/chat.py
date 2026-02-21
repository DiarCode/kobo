"""Chat endpoints with streaming support."""

from __future__ import annotations

import asyncio
import json
import logging

from app.agentservice.core.config import get_settings
from app.agentservice.services.chat_service import ChatService
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()
chat_service = ChatService()


class ChatRequest(BaseModel):
    """Request model for chat."""

    message: str
    workspace_context: str | None = None
    conversation_history: list[dict[str, str]] | None = None
    task_context: str | None = None
    temperature: float | None = None
    stream: bool = False


class ChatResponse(BaseModel):
    """Response model for chat."""

    response: str
    model_used: str | None = None
    fallback_used: bool = False
    warning: str | None = None


@router.post("/complete", response_model=ChatResponse)
async def chat_complete(request: ChatRequest) -> ChatResponse:
    """Complete a chat request without streaming."""
    try:
        temperature = request.temperature or settings.agent_default_temperature
        result = await chat_service.complete(
            message=request.message,
            workspace_context=request.workspace_context,
            conversation_history=request.conversation_history,
            task_context=request.task_context,
            temperature=temperature,
        )
        return ChatResponse(
            response=result["response"],
            model_used=result.get("model_used"),
            fallback_used=result.get("fallback_used", False),
            warning=result.get("warning"),
        )
    except Exception as e:
        logger.error(f"Chat completion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete/stream")
async def chat_complete_stream(request: ChatRequest):
    """Complete a chat request with streaming response."""
    async def generate():
        """Generate streaming response."""
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': request.message[:50] + '...'})}\n\n"

            temperature = request.temperature or settings.agent_default_temperature
            result = await chat_service.complete(
                message=request.message,
                workspace_context=request.workspace_context,
                conversation_history=request.conversation_history,
                task_context=request.task_context,
                temperature=temperature,
            )

            # Stream the response content in chunks
            content = result["response"]
            chunk_size = 30  # characters per chunk for typing effect
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.015)  # Small delay for visual effect

            # Send final result
            yield f"data: {json.dumps({'type': 'complete', 'response': content, 'model_used': result.get('model_used')})}\n\n"

        except Exception as e:
            logger.error(f"Chat streaming failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
