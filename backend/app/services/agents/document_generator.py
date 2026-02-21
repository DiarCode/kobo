"""Document generator service for creating formatted Markdown documents."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class DocumentGenerator:
    """Service for generating formatted documents from agent output and artifacts."""

    async def generate_markdown(
        self,
        title: str,
        content: str,
        artifact_type: str = "note",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Generate a formatted Markdown document."""
        metadata = metadata or {}
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        parts = [
            f"# {title}\n",
            f"**Type:** {artifact_type}\n",
            f"**Generated:** {now}\n",
        ]

        if metadata.get("source_run_id"):
            parts.append(f"**Source Agent Run:** {metadata['source_run_id']}\n")

        parts.append("\n---\n\n")
        parts.append(content)

        # Add metadata section if available
        if metadata:
            parts.append("\n\n---\n\n## Metadata\n\n")
            for key, value in metadata.items():
                if key not in ("format", "generated_at", "source_run_id"):
                    parts.append(f"- **{key.replace('_', ' ').title()}:** {value}\n")

        return "".join(parts)

    async def generate_from_agent_output(
        self,
        role_key: str,
        output: dict[str, Any],
        title: str,
    ) -> str:
        """Generate a Markdown document from agent execution output."""
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        parts = [
            f"# {title}\n",
            f"**Agent:** {role_key}\n",
            f"**Generated:** {now}\n",
            "\n---\n\n",
        ]

        # Executive summary
        summary = output.get("executive_summary", "")
        if summary:
            parts.append(f"## Executive Summary\n\n{summary}\n\n")

        # Full content
        full_content = output.get("full_content", "")
        if full_content:
            parts.append(f"## Details\n\n{full_content}\n\n")

        # Grounded claims
        claims = output.get("grounded_claims", [])
        if claims:
            parts.append("## Grounded Claims\n\n")
            for claim in claims:
                claim_text = claim.get("claim", "") if isinstance(claim, dict) else str(claim)
                parts.append(f"- {claim_text}\n")
            parts.append("\n")

        # Assumptions
        assumptions = output.get("assumptions", [])
        if assumptions:
            parts.append("## Assumptions\n\n")
            for assumption in assumptions:
                if isinstance(assumption, dict):
                    text = assumption.get("text", "")
                    risk = assumption.get("risk", "unknown")
                    parts.append(f"- **{risk.upper()}**: {text}\n")
                else:
                    parts.append(f"- {assumption}\n")
            parts.append("\n")

        # Confidence
        confidence = output.get("confidence_score", 0)
        if confidence:
            parts.append(f"## Confidence Score\n\n{confidence:.1%}\n\n")

        # Open questions
        questions = output.get("open_questions", [])
        if questions:
            parts.append("## Open Questions\n\n")
            for question in questions:
                parts.append(f"- {question}\n")
            parts.append("\n")

        # Review flags
        flags = output.get("review_flags", [])
        if flags:
            parts.append("## Review Required\n\n")
            for flag in flags:
                parts.append(f"- ⚠️ {flag}\n")
            parts.append("\n")

        return "".join(parts)


# Singleton instance
DOCUMENT_GENERATOR = DocumentGenerator()
