from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import ApprovalCreateIn, ApprovalDecisionIn, ApprovalOut, ApprovalStatus
from app.services.orchestration.approval import create_audit, enforce_external_action_policy
from app.services.orchestration.event_bus import EVENT_BUS

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("", response_model=ApprovalOut)
def create_approval(payload: ApprovalCreateIn, user: dict[str, object] = Depends(get_current_user)) -> ApprovalOut:
    require_workspace_member(payload.workspace_id, str(user["id"]))
    approval_id = STORE.new_id()
    record = {
        "id": approval_id,
        "workspace_id": payload.workspace_id,
        "task_id": payload.task_id,
        "status": ApprovalStatus.pending.value,
        "action_plan": payload.action_plan.model_dump(),
        "diff_preview": payload.diff_preview,
        "decision_note": None,
        "created_at": STORE.now_iso(),
    }
    STORE.approvals[approval_id] = record
    EVENT_BUS.publish("approval.requested", payload.workspace_id, {"approval_id": approval_id})
    return ApprovalOut(
        id=approval_id,
        workspace_id=payload.workspace_id,
        task_id=payload.task_id,
        status=ApprovalStatus.pending,
        action_plan=payload.action_plan,
        diff_preview=payload.diff_preview,
        decision_note=None,
        created_at=datetime.fromisoformat(str(record["created_at"])),
    )


@router.get("", response_model=list[ApprovalOut])
def list_approvals(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[ApprovalOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    approvals = [approval for approval in STORE.approvals.values() if approval["workspace_id"] == workspace_id]
    return [
        ApprovalOut(
            id=str(approval["id"]),
            workspace_id=str(approval["workspace_id"]),
            task_id=approval.get("task_id"),
            status=str(approval["status"]),
            action_plan=approval["action_plan"],
            diff_preview=approval.get("diff_preview"),
            decision_note=approval.get("decision_note"),
            created_at=datetime.fromisoformat(str(approval["created_at"])),
        )
        for approval in approvals
    ]


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
def approve(
    approval_id: str,
    payload: ApprovalDecisionIn,
    user: dict[str, object] = Depends(get_current_user),
) -> ApprovalOut:
    approval = STORE.approvals.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    workspace_id = str(approval["workspace_id"])
    require_workspace_member(workspace_id, str(user["id"]))
    try:
        enforce_external_action_policy(str(approval["action_plan"]["action_type"]), ApprovalStatus.approved)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    approval["status"] = ApprovalStatus.approved.value
    approval["decision_note"] = payload.note
    create_audit(workspace_id, "user", str(user["id"]), "approval.approve", "approval", approval_id, approval)
    EVENT_BUS.publish("approval.approved", workspace_id, {"approval_id": approval_id})
    return ApprovalOut(
        id=str(approval["id"]),
        workspace_id=workspace_id,
        task_id=approval.get("task_id"),
        status=ApprovalStatus.approved,
        action_plan=approval["action_plan"],
        diff_preview=approval.get("diff_preview"),
        decision_note=payload.note,
        created_at=datetime.fromisoformat(str(approval["created_at"])),
    )


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
def reject(
    approval_id: str,
    payload: ApprovalDecisionIn,
    user: dict[str, object] = Depends(get_current_user),
) -> ApprovalOut:
    approval = STORE.approvals.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    workspace_id = str(approval["workspace_id"])
    require_workspace_member(workspace_id, str(user["id"]))
    approval["status"] = ApprovalStatus.rejected.value
    approval["decision_note"] = payload.note
    create_audit(workspace_id, "user", str(user["id"]), "approval.reject", "approval", approval_id, approval)
    EVENT_BUS.publish("approval.rejected", workspace_id, {"approval_id": approval_id})
    return ApprovalOut(
        id=str(approval["id"]),
        workspace_id=workspace_id,
        task_id=approval.get("task_id"),
        status=ApprovalStatus.rejected,
        action_plan=approval["action_plan"],
        diff_preview=approval.get("diff_preview"),
        decision_note=payload.note,
        created_at=datetime.fromisoformat(str(approval["created_at"])),
    )
