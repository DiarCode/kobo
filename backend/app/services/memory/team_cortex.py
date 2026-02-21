from __future__ import annotations

from dataclasses import dataclass

from app.core.store import STORE
from app.domain.schemas import EvidenceRef


@dataclass(slots=True)
class TeamCortexService:
    def add_evidence(
        self,
        workspace_id: str,
        task_id: str | None,
        run_id: str | None,
        claim: str,
        source_type: str,
        source_ref: str,
        confidence: float,
    ) -> EvidenceRef:
        record_id = STORE.new_id()
        STORE.evidence_entries.append(
            {
                "id": record_id,
                "workspace_id": workspace_id,
                "task_id": task_id,
                "run_id": run_id,
                "claim": claim,
                "source_type": source_type,
                "source_ref": source_ref,
                "confidence": confidence,
                "created_at": STORE.now_iso(),
            }
        )
        return EvidenceRef(
            id=record_id,
            source_type=source_type,
            source_ref=source_ref,
            confidence=confidence,
        )

    def by_task(self, task_id: str) -> list[dict[str, object]]:
        return [entry for entry in STORE.evidence_entries if entry.get("task_id") == task_id]


TEAM_CORTEX = TeamCortexService()
