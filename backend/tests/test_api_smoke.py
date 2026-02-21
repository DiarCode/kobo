from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.store import STORE
from app.main import app

client = TestClient(app)


def _register_user(api_client: TestClient, prefix: str = "owner") -> str:
    username = f"{prefix}-{uuid4().hex[:8]}"
    register = api_client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "Password123!"},
    )
    assert register.status_code == 200
    return username


def auth_headers() -> dict[str, str]:
    _ = _register_user(client, prefix="owner")
    return {}


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["service"] == "KOBO Backend"


def test_task_proof_gate_flow() -> None:
    _ = auth_headers()

    workspace = client.post(
        "/api/v1/workspaces",
        json={"name": "Acme", "slug": "acme", "template": "Feature Sprint"},
    )
    assert workspace.status_code == 200
    workspace_id = workspace.json()["id"]

    task = client.post(
        "/api/v1/tasks",
        json={
            "workspace_id": workspace_id,
            "title": "Implement API",
            "description": "Build endpoints",
            "acceptance_criteria": ["Tests pass"],
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    blocked_done = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})
    assert blocked_done.status_code == 400

    artifact = client.post(
        "/api/v1/artifacts",
        json={
            "workspace_id": workspace_id,
            "task_id": task_id,
            "type": "spec",
            "title": "Spec v1",
            "content": "Done criteria met",
            "metadata": {},
        },
    )
    assert artifact.status_code == 200

    done = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})
    assert done.status_code == 200
    assert done.json()["status"] == "done"


def test_invite_link_uses_frontend_url_and_actions_required_is_system_only() -> None:
    _ = auth_headers()
    workspace = client.post(
        "/api/v1/workspaces",
        json={"name": "Team", "slug": f"team-{uuid4().hex[:6]}", "template": "Feature Sprint"},
    )
    assert workspace.status_code == 200
    workspace_id = workspace.json()["id"]

    invite = client.get(f"/api/v1/workspaces/{workspace_id}/invite-link")
    assert invite.status_code == 200
    assert invite.json()["invite_url"].startswith("http://localhost:5173/invite/")

    blocked_action = client.post(
        f"/api/v1/workspaces/{workspace_id}/actions-required",
        json={"title": "manual", "description": "manual", "severity": "high"},
    )
    assert blocked_action.status_code == 403


def test_task_and_run_timeline_endpoints_shape_and_authz() -> None:
    owner_client = TestClient(app)
    _ = _register_user(owner_client, prefix="owner")

    workspace = owner_client.post(
        "/api/v1/workspaces",
        json={"name": "Timeline", "slug": f"timeline-{uuid4().hex[:6]}", "template": "Feature Sprint"},
    )
    assert workspace.status_code == 200
    workspace_id = workspace.json()["id"]

    task = owner_client.post(
        "/api/v1/tasks",
        json={
            "workspace_id": workspace_id,
            "title": "Inspect agent timeline",
            "description": "Ensure timeline endpoint shape",
            "acceptance_criteria": ["Timeline returns ordered stages"],
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    run_id = STORE.new_id()
    STORE.agent_runs[run_id] = {
        "id": run_id,
        "workspace_id": workspace_id,
        "task_id": task_id,
        "role_key": "project_manager",
        "status": "completed",
        "created_at": STORE.now_iso(),
        "updated_at": STORE.now_iso(),
        "output": None,
    }
    STORE.agent_run_timelines[run_id].append(
        {
            "id": STORE.new_id(),
            "run_id": run_id,
            "task_id": task_id,
            "workspace_id": workspace_id,
            "stage": "planner",
            "agent_role": "project_manager",
            "title": "Planning",
            "summary": "Built task execution plan.",
            "status": "completed",
            "created_at": STORE.now_iso(),
            "metadata": {"step_index": 2},
        }
    )

    task_timeline = owner_client.get(f"/api/v1/tasks/{task_id}/agent-timeline")
    assert task_timeline.status_code == 200
    task_items = task_timeline.json()
    assert len(task_items) == 1
    assert task_items[0]["run_id"] == run_id
    assert task_items[0]["stage"] == "planner"
    assert task_items[0]["status"] == "completed"

    run_timeline = owner_client.get(f"/api/v1/agent-runs/{run_id}/timeline")
    assert run_timeline.status_code == 200
    run_items = run_timeline.json()
    assert len(run_items) == 1
    assert run_items[0]["task_id"] == task_id
    assert run_items[0]["metadata"]["step_index"] == 2

    outsider_client = TestClient(app)
    _ = _register_user(outsider_client, prefix="outsider")
    forbidden = outsider_client.get(f"/api/v1/tasks/{task_id}/agent-timeline")
    assert forbidden.status_code == 403


def test_subtasks_crud_agent_delete_and_assistant_voice_token() -> None:
    api_client = TestClient(app)
    _ = _register_user(api_client, prefix="workspace")

    workspace = api_client.post(
        "/api/v1/workspaces",
        json={"name": "Execution", "slug": f"execution-{uuid4().hex[:6]}", "template": "Feature Sprint"},
    )
    assert workspace.status_code == 200
    workspace_id = workspace.json()["id"]

    task = api_client.post(
        "/api/v1/tasks",
        json={
            "workspace_id": workspace_id,
            "title": "Ship launch page",
            "description": "Create launch and QA subtasks",
            "acceptance_criteria": ["Ship completed"],
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    created_subtasks = api_client.post(
        f"/api/v1/tasks/{task_id}/subtasks",
        json={"title": "Draft copy", "description": "First pass"},
    )
    assert created_subtasks.status_code == 200
    subtask_id = created_subtasks.json()[0]["id"]

    updated_subtasks = api_client.patch(
        f"/api/v1/tasks/{task_id}/subtasks/{subtask_id}",
        json={"status": "in_progress"},
    )
    assert updated_subtasks.status_code == 200
    assert updated_subtasks.json()[0]["status"] == "in_progress"

    deleted_subtasks = api_client.delete(f"/api/v1/tasks/{task_id}/subtasks/{subtask_id}")
    assert deleted_subtasks.status_code == 200
    assert deleted_subtasks.json() == []

    created_agent = api_client.post(
        f"/api/v1/workspaces/{workspace_id}/agents",
        json={"role_key": "researcher", "full_name": "Rae Vega"},
    )
    assert created_agent.status_code == 200
    agent_id = created_agent.json()["id"]

    deleted_agent = api_client.delete(f"/api/v1/workspaces/{workspace_id}/agents/{agent_id}")
    assert deleted_agent.status_code == 200
    assert deleted_agent.json()["message"] == "Agent deleted"

    voice_token = api_client.post(f"/api/v1/assistant/workspaces/{workspace_id}/voice/token")
    assert voice_token.status_code == 200
    payload = voice_token.json()
    assert payload["workspace_id"] == workspace_id
    assert payload["room"].startswith("kobo-")
    assert isinstance(payload["token"], str) and len(payload["token"]) > 20
