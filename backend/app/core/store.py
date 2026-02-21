from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class InMemoryStore:
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    users_by_username: dict[str, str] = field(default_factory=dict)
    workspaces: dict[str, dict[str, Any]] = field(default_factory=dict)
    workspace_members: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    workspace_member_profiles: dict[str, dict[str, dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    workspace_invites: dict[str, dict[str, Any]] = field(default_factory=dict)
    workspace_task_statuses: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    workspace_agents: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    workspace_files: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    workspace_actions_required: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    projects: dict[str, dict[str, Any]] = field(default_factory=dict)
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    task_subtasks: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    task_dependencies: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    task_comments: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    task_attachments: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    evidence_entries: list[dict[str, Any]] = field(default_factory=list)
    agent_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_run_timelines: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    workspace_assistant_messages: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    approvals: dict[str, dict[str, Any]] = field(default_factory=dict)
    decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    integration_accounts: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    audit_logs: list[dict[str, Any]] = field(default_factory=list)
    eval_runs: list[dict[str, Any]] = field(default_factory=list)

    def new_id(self) -> str:
        return str(uuid4())

    def now_iso(self) -> str:
        return datetime.now(UTC).isoformat()


STORE = InMemoryStore()
