from __future__ import annotations

from app.core.store import STORE
from app.domain.schemas import ApprovalStatus

EXTERNAL_WRITE_ACTIONS = {
    "github.create_pr",
    "github.push_commit",
    "linear.create_issue",
    "linear.update_issue",
    "slack.post_message",
}


def requires_human_gate(action_type: str) -> bool:
    return action_type in EXTERNAL_WRITE_ACTIONS


def create_audit(
    workspace_id: str,
    actor_type: str,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, object] | None = None,
) -> None:
    STORE.audit_logs.append(
        {
            "id": STORE.new_id(),
            "workspace_id": workspace_id,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "payload": payload or {},
            "created_at": STORE.now_iso(),
        }
    )


def enforce_external_action_policy(action_type: str, status: ApprovalStatus) -> None:
    if requires_human_gate(action_type) and status != ApprovalStatus.approved:
        raise ValueError("External write actions require approved status")
