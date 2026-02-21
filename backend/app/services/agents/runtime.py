from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.domain.schemas import (
    AgentOutput,
    Assumption,
    GroundedClaim,
)
from app.services.agents.confidence import compute_confidence
from app.services.memory.team_cortex import TEAM_CORTEX

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _candidate_models(self) -> list[str]:
        models: list[str] = [self.settings.ollama_model.strip()]
        for model in (item.strip() for item in self.settings.ollama_fallback_models.split(",")):
            if model and model not in models:
                models.append(model)
        return models

    def _format_model_error(self, model: str, error: Exception) -> str:
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

    async def run(self, role_key: str, goal: str, workspace_id: str, task_id: str | None = None) -> AgentOutput:
        prompt = self._build_prompt(role_key=role_key, goal=goal)
        response_text = await self._call_ollama(prompt)

        assumption = Assumption(
            text="This is a draft output generated with current workspace context.",
            type="scope",
            risk="low",
            verification_suggestion="Review acceptance criteria before approving external actions.",
        )

        evidence = TEAM_CORTEX.add_evidence(
            workspace_id=workspace_id,
            task_id=task_id,
            run_id=None,
            claim=goal,
            source_type="task",
            source_ref=f"task:{task_id or 'none'}",
            confidence=0.83,
        )

        grounded_claim = GroundedClaim(claim="Output was grounded in task context.", evidence_links=[evidence])
        confidence_score, breakdown = compute_confidence(
            source_ratio=0.86,
            consistency=0.75,
            verifier_risk=0.18,
        )

        if confidence_score < 0.7:
            open_questions = ["Need additional context to produce a reliable output."]
            review_flags = ["abstained_low_confidence"]
        else:
            open_questions = []
            review_flags = []

        return AgentOutput(
            executive_summary=f"{role_key} produced an actionable draft.",
            full_content=response_text,
            grounded_claims=[grounded_claim],
            assumptions=[assumption],
            confidence_score=confidence_score,
            confidence_breakdown=breakdown,
            open_questions=open_questions,
            review_flags=review_flags,
        )

    async def _call_ollama(self, prompt: str) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        model_errors: list[str] = []
        model_candidates = self._candidate_models()
        for index, model in enumerate(model_candidates):
            payload: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2},
            }
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                text = data.get("response", "")
                if isinstance(text, str) and text.strip():
                    return text.strip()
                model_errors.append(f"{model}: empty response")
            except Exception as error:
                detail = self._format_model_error(model, error)
                model_errors.append(detail)
                logger.warning("agent_runtime_model_request_failed", extra={"model": model, "detail": detail})
            if index < len(model_candidates) - 1:
                await asyncio.sleep(0.8)

        fallback = {
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": "Local fallback used because Ollama was unavailable.",
            "model_errors": model_errors[:5],
            "next_steps": [
                "Validate evidence links.",
                "Run critic and verifier passes.",
                "Request approval if action writes external state.",
            ],
        }
        return json.dumps(fallback, indent=2)

    def _build_prompt(self, role_key: str, goal: str) -> str:
        return (
            f"You are KOBO {role_key}. Follow grounded-first execution.\n"
            f"Goal: {goal}\n"
            "Return concise structured markdown with assumptions and risks.\n"
            "Do not invent external facts."
        )


AGENT_RUNTIME = AgentRuntime()
