from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import CouncilCreateIn, CouncilSessionOut, DecisionArtifactOut
from app.services.agents.council import COUNCIL_SERVICE
from app.services.orchestration.event_bus import EVENT_BUS

router = APIRouter(tags=["council"])


@router.post("/council/sessions", response_model=CouncilSessionOut)
async def create_council_session(
    payload: CouncilCreateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> CouncilSessionOut:
    require_workspace_member(payload.workspace_id, str(user["id"]))
    decision = await COUNCIL_SERVICE.deliberate(payload.workspace_id, payload.question, payload.task_id)
    session_id = STORE.new_id()
    session = {
        "id": session_id,
        "workspace_id": payload.workspace_id,
        "status": "completed",
        "stage": "synthesized",
        "decision": decision.model_dump(),
    }
    STORE.agent_runs[session_id] = session
    EVENT_BUS.publish("council.session.completed", payload.workspace_id, {"session_id": session_id})
    return CouncilSessionOut(**session)


@router.get("/council/sessions/{session_id}", response_model=CouncilSessionOut)
def get_session(session_id: str, user: dict[str, object] = Depends(get_current_user)) -> CouncilSessionOut:
    session = STORE.agent_runs.get(session_id)
    if session is None or "decision" not in session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    require_workspace_member(str(session["workspace_id"]), str(user["id"]))
    return CouncilSessionOut(**session)


@router.get("/decisions/{decision_id}", response_model=DecisionArtifactOut)
def get_decision(decision_id: str, user: dict[str, object] = Depends(get_current_user)) -> DecisionArtifactOut:
    decision = STORE.decisions.get(decision_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    require_workspace_member(str(decision["workspace_id"]), str(user["id"]))
    return DecisionArtifactOut(**decision)
