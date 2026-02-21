from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import AgentRunCreateIn, AgentRunOut, AgentRunTimelineOut
from app.services.orchestration.orchestrator import ORCHESTRATOR_SERVICE

router = APIRouter(tags=["agents"])

DEFAULT_AGENT_PROFILES: list[dict[str, str]] = [
    {
        "key": "project_manager",
        "display_name": "Mira Patel",
        "title": "Project Manager",
        "tone": "decisive",
        "character": "structured and delivery-focused",
        "system_prompt": "Drive execution, de-risk scope, and produce clear task plans with tradeoffs.",
        "avatar_key": "char1",
    },
    {
        "key": "growth",
        "display_name": "Ava Brooks",
        "title": "Growth",
        "tone": "analytic",
        "character": "experiment-driven and metric-oriented",
        "system_prompt": "Propose growth experiments with measurable hypotheses and instrumentation.",
        "avatar_key": "char1",
    },
    {
        "key": "finance",
        "display_name": "Liam Carter",
        "title": "Finance",
        "tone": "conservative",
        "character": "risk-aware and numbers-first",
        "system_prompt": "Evaluate budgets and financial risks with conservative assumptions.",
        "avatar_key": "char2",
    },
    {
        "key": "legal_officer",
        "display_name": "Daniel Reed",
        "title": "Legal Officer",
        "tone": "formal",
        "character": "compliance-minded and exact",
        "system_prompt": "Flag legal/compliance concerns and demand explicit approvals for write actions.",
        "avatar_key": "char1",
    },
    {
        "key": "critic",
        "display_name": "Priya Shah",
        "title": "Critic",
        "tone": "skeptical",
        "character": "red-team and contradiction-focused",
        "system_prompt": "Stress-test outputs, surface unsupported claims, and challenge weak assumptions.",
        "avatar_key": "char2",
    },
    {
        "key": "researcher",
        "display_name": "Iris Moreno",
        "title": "Researcher",
        "tone": "curious",
        "character": "methodical and source-focused",
        "system_prompt": "Gather and synthesize evidence with provenance and clear confidence bounds.",
        "avatar_key": "char1",
    },
]


def _timeline_out(item: dict[str, object]) -> AgentRunTimelineOut:
    return AgentRunTimelineOut(
        id=str(item["id"]),
        run_id=str(item["run_id"]),
        task_id=item.get("task_id"),
        workspace_id=str(item["workspace_id"]),
        stage=str(item["stage"]),
        agent_role=str(item["agent_role"]),
        title=str(item["title"]),
        summary=str(item["summary"]),
        status=str(item["status"]),
        metadata=dict(item.get("metadata", {})),
        created_at=datetime.fromisoformat(str(item["created_at"])),
    )


@router.get("/agents")
def list_agent_roles() -> dict[str, list[dict[str, str]]]:
    return {"roles": DEFAULT_AGENT_PROFILES}


@router.post("/agent-runs", response_model=AgentRunOut)
async def run_agent(payload: AgentRunCreateIn, user: dict[str, object] = Depends(get_current_user)) -> AgentRunOut:
    require_workspace_member(payload.workspace_id, str(user["id"]))
    record = await ORCHESTRATOR_SERVICE.execute(payload)
    return AgentRunOut(
        id=str(record["id"]),
        workspace_id=str(record["workspace_id"]),
        task_id=record.get("task_id"),
        role_key=str(record["role_key"]),
        status=str(record["status"]),
        output=record.get("output"),
        created_at=datetime.fromisoformat(str(record["created_at"])),
        updated_at=datetime.fromisoformat(str(record["updated_at"])),
    )


@router.get("/agent-runs", response_model=list[AgentRunOut])
def list_runs(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[AgentRunOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    runs = [
        run
        for run in STORE.agent_runs.values()
        if run.get("workspace_id") == workspace_id and "role_key" in run
    ]
    return [
        AgentRunOut(
            id=str(run["id"]),
            workspace_id=str(run["workspace_id"]),
            task_id=run.get("task_id"),
            role_key=str(run["role_key"]),
            status=str(run["status"]),
            output=run.get("output"),
            created_at=datetime.fromisoformat(str(run["created_at"])),
            updated_at=datetime.fromisoformat(str(run["updated_at"])),
        )
        for run in runs
    ]


@router.get("/agent-runs/{run_id}", response_model=AgentRunOut)
def get_run(run_id: str, user: dict[str, object] = Depends(get_current_user)) -> AgentRunOut:
    run = STORE.agent_runs.get(run_id)
    if run is None or "role_key" not in run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    require_workspace_member(str(run["workspace_id"]), str(user["id"]))
    return AgentRunOut(
        id=str(run["id"]),
        workspace_id=str(run["workspace_id"]),
        task_id=run.get("task_id"),
        role_key=str(run["role_key"]),
        status=str(run["status"]),
        output=run.get("output"),
        created_at=datetime.fromisoformat(str(run["created_at"])),
        updated_at=datetime.fromisoformat(str(run["updated_at"])),
    )


@router.get("/agent-runs/{run_id}/events")
def get_run_events(run_id: str, user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    run = STORE.agent_runs.get(run_id)
    if run is None or "role_key" not in run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    require_workspace_member(str(run["workspace_id"]), str(user["id"]))
    events = [
        {
            "id": log["id"],
            "action": log["action"],
            "created_at": log["created_at"],
            "payload": log.get("payload", {}),
        }
        for log in STORE.audit_logs
        if log.get("entity_type") == "agent_run" and log.get("entity_id") == run_id
    ]
    return {"run_id": run_id, "events": events}


@router.get("/agent-runs/{run_id}/timeline", response_model=list[AgentRunTimelineOut])
def get_run_timeline(run_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[AgentRunTimelineOut]:
    run = STORE.agent_runs.get(run_id)
    if run is None or "role_key" not in run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    require_workspace_member(str(run["workspace_id"]), str(user["id"]))
    timeline = STORE.agent_run_timelines.get(run_id, [])
    ordered = sorted(timeline, key=lambda item: str(item.get("created_at", "")))
    return [_timeline_out(item) for item in ordered]
