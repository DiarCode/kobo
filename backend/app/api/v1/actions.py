from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("/{action_id}/plan")
def get_action_plan(action_id: str, user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    return {
        "action_id": action_id,
        "requested_by": user["id"],
        "plan": [
            "Validate permissions",
            "Show diff preview",
            "Require explicit approval",
            "Execute and record immutable audit log",
        ],
        "signed": True,
    }
