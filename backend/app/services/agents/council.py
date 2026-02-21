from __future__ import annotations

from dataclasses import dataclass

from app.core.store import STORE
from app.domain.schemas import DecisionArtifactOut
from app.services.agents.confidence import compute_confidence


@dataclass(slots=True)
class CouncilService:
    async def deliberate(self, workspace_id: str, question: str, task_id: str | None = None) -> DecisionArtifactOut:
        dissenting_views = [
            "Builder prefers staged rollout over immediate release.",
            "Critic requires explicit rollback plan in action plan.",
        ]

        confidence, _ = compute_confidence(0.9, 0.78, 0.12)
        decision_id = STORE.new_id()
        decision = {
            "id": decision_id,
            "workspace_id": workspace_id,
            "question": question,
            "task_id": task_id,
            "recommendation": "Proceed with feature-flag rollout and human approval for external writes.",
            "dissenting_views": dissenting_views,
            "confidence": confidence,
            "consensus_score": 0.71,
            "created_at": STORE.now_iso(),
            "final_decision": None,
            "rationale": None,
        }
        STORE.decisions[decision_id] = decision
        return DecisionArtifactOut(**decision)


COUNCIL_SERVICE = CouncilService()
