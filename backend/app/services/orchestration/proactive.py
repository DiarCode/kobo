from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.store import STORE


@dataclass(slots=True)
class ProactiveSignal:
    priority: str
    signal_type: str
    task_id: str | None
    summary: str


class ProactiveEngine:
    def detect_stalled_tasks(self, workspace_id: str, threshold_days: int = 3) -> list[ProactiveSignal]:
        now = datetime.now(UTC)
        signals: list[ProactiveSignal] = []
        for task in STORE.tasks.values():
            if task["workspace_id"] != workspace_id:
                continue
            if task["status"] != "in_progress":
                continue
            updated_at = datetime.fromisoformat(task["updated_at"])
            if updated_at < (now - timedelta(days=threshold_days)):
                signals.append(
                    ProactiveSignal(
                        priority="high",
                        signal_type="task_stalled",
                        task_id=task["id"],
                        summary=f"Task {task['title']} stalled for more than {threshold_days} days.",
                    )
                )
        return signals


PROACTIVE_ENGINE = ProactiveEngine()
