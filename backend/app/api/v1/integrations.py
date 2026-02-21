from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import IntegrationActionIn, IntegrationConnectOut
from app.services.integrations.github import GITHUB_INTEGRATION
from app.services.integrations.linear import LINEAR_INTEGRATION
from app.services.orchestration.approval import create_audit

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/{provider}/connect", response_model=IntegrationConnectOut)
def connect(provider: str, user: dict[str, object] = Depends(get_current_user)) -> IntegrationConnectOut:
    state = f"{provider}:{user['id']}"
    if provider == "github":
        url = GITHUB_INTEGRATION.authorize_url(state)
    elif provider == "linear":
        url = LINEAR_INTEGRATION.authorize_url(state)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported provider")
    return IntegrationConnectOut(provider=provider, authorize_url=url)


@router.post("/github/issues")
def create_github_issue(payload: IntegrationActionIn, user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    require_workspace_member(payload.workspace_id, str(user["id"]))
    create_audit(
        payload.workspace_id,
        "user",
        str(user["id"]),
        "github.issue.create",
        "task",
        payload.task_id,
        payload.model_dump(),
    )
    return {"status": "queued", "provider": "github", "title": payload.title}


@router.post("/linear/issues")
def create_linear_issue(payload: IntegrationActionIn, user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    require_workspace_member(payload.workspace_id, str(user["id"]))
    create_audit(
        payload.workspace_id,
        "user",
        str(user["id"]),
        "linear.issue.create",
        "task",
        payload.task_id,
        payload.model_dump(),
    )
    return {"status": "queued", "provider": "linear", "title": payload.title}


@router.get("/{workspace_id}/accounts")
def list_accounts(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    require_workspace_member(workspace_id, str(user["id"]))
    return {"workspace_id": workspace_id, "accounts": STORE.integration_accounts.get(workspace_id, [])}
