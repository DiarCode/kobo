from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import AutonomyScore, EvalRunOut
from app.services.orchestration.autonomy import compute_autonomy
from app.services.orchestration.proactive import PROACTIVE_ENGINE

router = APIRouter(tags=["metrics"])


@router.get("/autonomy-scores", response_model=list[AutonomyScore])
def autonomy_scores(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[AutonomyScore]:
    require_workspace_member(workspace_id, str(user["id"]))
    run_count = len([r for r in STORE.agent_runs.values() if r.get("workspace_id") == workspace_id and "role_key" in r])
    successes = len(
        [
            r
            for r in STORE.agent_runs.values()
            if r.get("workspace_id") == workspace_id and r.get("status") == "completed" and "role_key" in r
        ]
    )
    computed = compute_autonomy(successes, max(run_count, 1))
    return [
        AutonomyScore(
            workspace_id=workspace_id,
            role_key="builder",
            action_type="github.create_pr",
            score=computed.score,
            lower_bound95=computed.lower_bound95,
            tier=computed.tier,
            sample_size=run_count,
        )
    ]


@router.get("/eval-runs", response_model=list[EvalRunOut])
def eval_runs(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[EvalRunOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    return [
        EvalRunOut(
            id=str(item["id"]),
            workspace_id=str(item["workspace_id"]),
            run_type=str(item["run_type"]),
            grounding_rate=item.get("grounding_rate"),
            first_pass_approval=item.get("first_pass_approval"),
            unsupported_claim_rate=item.get("unsupported_claim_rate"),
            p95_latency_ms=item.get("p95_latency_ms"),
            cost_per_task=item.get("cost_per_task"),
            created_at=datetime.fromisoformat(str(item["created_at"])),
        )
        for item in STORE.eval_runs
        if item.get("workspace_id") == workspace_id
    ]


@router.get("/proactive/signals")
def proactive_signals(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    require_workspace_member(workspace_id, str(user["id"]))
    signals = [signal.__dict__ for signal in PROACTIVE_ENGINE.detect_stalled_tasks(workspace_id)]
    return {"workspace_id": workspace_id, "signals": signals}
