from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE

router = APIRouter(prefix="/evidence-ledger", tags=["evidence"])


@router.get("/task/{task_id}")
def evidence_by_task(task_id: str, user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    task = STORE.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    workspace_id = str(task["workspace_id"])
    require_workspace_member(workspace_id, str(user["id"]))
    entries = [entry for entry in STORE.evidence_entries if entry.get("task_id") == task_id]
    return {"task_id": task_id, "entries": entries}
