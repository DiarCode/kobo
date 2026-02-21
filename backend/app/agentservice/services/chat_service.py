"""Chat service - handles workspace assistant chat."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from app.agentservice.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatService:
    """Service for workspace assistant chat."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _candidate_models(self) -> list[str]:
        """Get list of candidate models."""
        models: list[str] = [self.settings.ollama_model.strip()]
        for model in (item.strip() for item in self.settings.ollama_fallback_models.split(",")):
            if model and model not in models:
                models.append(model)
        return models

    def _format_model_error(self, model: str, error: Exception) -> str:
        """Format model error message."""
        if isinstance(error, httpx.HTTPStatusError):
            detail = error.response.text.strip()
            try:
                payload = error.response.json()
                if isinstance(payload, dict) and isinstance(payload.get("error"), str):
                    detail = payload["error"]
            except ValueError:
                pass
            detail = " ".join(detail.split())
            return f"{model}: HTTP {error.response.status_code} {detail[:220]}"
        detail = " ".join(str(error).split())
        return f"{model}: {detail[:220] or error.__class__.__name__}"

    async def complete(
        self,
        message: str,
        workspace_context: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        task_context: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Complete a chat request."""
        prompt = self._build_prompt(
            message=message,
            workspace_context=workspace_context,
            conversation_history=conversation_history,
            task_context=task_context,
        )

        response_text, model_used, fallback_used = await self._call_ollama(prompt, temperature)

        warning: str | None = None
        if fallback_used:
            warning = f"Primary model failed. Used fallback model `{model_used}`."

        return {
            "response": response_text,
            "model_used": model_used,
            "fallback_used": fallback_used,
            "warning": warning,
        }

    async def _call_ollama(
        self, prompt: str, temperature: float
    ) -> tuple[str, str | None, bool]:
        """Call Ollama API with fallback models."""
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        model_errors: list[str] = []
        model_candidates = self._candidate_models()

        for index, model in enumerate(model_candidates):
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            }
            try:
                timeout = httpx.Timeout(self.settings.agent_timeout_seconds)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                candidate = data.get("response")
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip(), model, False
                model_errors.append(f"{model}: empty response")
            except Exception as error:
                detail = self._format_model_error(model, error)
                model_errors.append(detail)
                logger.warning("chat_model_request_failed", extra={"model": model, "detail": detail})
            if index < len(model_candidates) - 1:
                await asyncio.sleep(0.8)

        fallback = (
            "Assistant model unavailable right now. "
            f"Reason: {model_errors[-1] if model_errors else 'no model response'}. "
            "Try again in a moment."
        )
        return fallback, None, True

    def _build_prompt(
        self,
        message: str,
        workspace_context: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        task_context: str | None = None,
    ) -> str:
        """Build prompt for chat completion."""
        parts = [
            "You are KOBO Workspace Assistant.\n",
            "Rules:\n",
            "- Use only provided workspace context and user prompt.\n",
            "- If information is missing, say Unknown and ask a clear follow-up question.\n",
            "- Keep output concise and action-oriented.\n",
            "- For reports, include sections and bullet points.\n\n",
        ]

        if workspace_context:
            parts.append(f"{workspace_context}\n")

        if task_context:
            parts.append(f"{task_context}\n")

        if conversation_history:
            history_lines = []
            for item in conversation_history[-12:]:  # Last 12 messages
                role = item.get("role", "").upper()
                content = item.get("content", "").strip()
                if content:
                    history_lines.append(f"{role}: {content}")
            if history_lines:
                parts.append("Recent conversation:\n")
                parts.append("\n".join(history_lines))
                parts.append("\n\n")

        parts.append(f"User request: {message}\n")

        return "".join(parts)


# Singleton instance
CHAT_SERVICE = ChatService()
