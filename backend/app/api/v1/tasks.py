from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import (
    ActivityItem,
    AgentRunCreateIn,
    AgentRunOut,
    DependencyCreateIn,
    ProofCheckOut,
    TaskAgentRevisionIn,
    TaskAgentTimelineOut,
    TaskAttachmentCreateIn,
    TaskAttachmentOut,
    TaskCommentCreateIn,
    TaskCommentOut,
    TaskCreateIn,
    TaskOut,
    TaskSubtaskCreateIn,
    TaskSubtaskOut,
    TaskSubtaskUpdateIn,
    TaskUpdateIn,
)
from app.services.orchestration.approval import create_audit
from app.services.orchestration.event_bus import EVENT_BUS
from app.services.orchestration.orchestrator import ORCHESTRATOR_SERVICE

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_out(task: dict[str, object]) -> TaskOut:
    return TaskOut(
        id=str(task["id"]),
        workspace_id=str(task["workspace_id"]),
        project_id=task.get("project_id"),
        title=str(task["title"]),
        description=task.get("description"),
        status=str(task["status"]),
        priority=str(task["priority"]),
        acceptance_criteria=list(task.get("acceptance_criteria", [])),
        assignee_user_id=task.get("assignee_user_id"),
        assignee_agent_role=task.get("assignee_agent_role"),
        proof_exempt=bool(task.get("proof_exempt", False)),
        created_at=datetime.fromisoformat(str(task["created_at"])),
        updated_at=datetime.fromisoformat(str(task["updated_at"])),
    )


def _has_cycle(task_id: str, depends_on_task_id: str) -> bool:
    graph = STORE.task_dependencies

    def dfs(current: str, target: str, visited: set[str]) -> bool:
        if current == target:
            return True
        visited.add(current)
        for nxt in graph.get(current, set()):
            if nxt not in visited and dfs(nxt, target, visited):
                return True
        return False

    return dfs(depends_on_task_id, task_id, set())


def _get_workspace_id_for_task(task_id: str) -> str:
    task = STORE.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return str(task["workspace_id"])


def _workspace_status_keys(workspace_id: str) -> set[str]:
    statuses = STORE.workspace_task_statuses.get(workspace_id) or []
    return {str(item["key"]) for item in statuses}


def _task_timeline_out(item: dict[str, object]) -> TaskAgentTimelineOut:
    return TaskAgentTimelineOut(
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


def _task_subtask_out(item: dict[str, object]) -> TaskSubtaskOut:
    return TaskSubtaskOut(
        id=str(item["id"]),
        task_id=str(item["task_id"]),
        workspace_id=str(item["workspace_id"]),
        title=str(item["title"]),
        description=item.get("description"),
        status=str(item["status"]),
        order=int(item["order"]),
        assignee_user_id=item.get("assignee_user_id"),
        assignee_agent_role=item.get("assignee_agent_role"),
        created_at=datetime.fromisoformat(str(item["created_at"])),
        updated_at=datetime.fromisoformat(str(item["updated_at"])),
    )


def _agent_run_out(run: dict[str, object]) -> AgentRunOut:
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


def _normalize_subtask_order(task_id: str) -> list[dict[str, object]]:
    items = STORE.task_subtasks.get(task_id, [])
    items.sort(key=lambda entry: int(entry.get("order", 0)))
    for index, item in enumerate(items):
        item["order"] = index
    return items


async def _run_assigned_agent(
    workspace_id: str,
    task_id: str,
    role_key: str,
    trigger_reason: str,
) -> None:
    active_exists = any(
        run.get("task_id") == task_id
        and str(run.get("workspace_id")) == workspace_id
        and str(run.get("role_key")) == role_key
        and str(run.get("status")) == "running"
        for run in STORE.agent_runs.values()
        if "role_key" in run
    )
    if active_exists:
        return

    task = STORE.tasks.get(task_id)
    if task is None:
        return

    goal = (
        f"Execute assigned task.\n"
        f"Title: {task.get('title')}\n"
        f"Description: {task.get('description') or 'n/a'}\n"
        f"Acceptance criteria: {', '.join(task.get('acceptance_criteria', [])) or 'n/a'}\n"
        f"Trigger: {trigger_reason}"
    )
    request = AgentRunCreateIn(
        workspace_id=workspace_id,
        task_id=task_id,
        role_key=role_key,
        goal=goal,
        stakes_level="medium",
    )
    record = await ORCHESTRATOR_SERVICE.execute(request)
    output = record.get("output") if isinstance(record.get("output"), dict) else {}
    open_questions = output.get("open_questions") if isinstance(output, dict) else []
    if isinstance(open_questions, list) and open_questions:
        action = {
            "id": STORE.new_id(),
            "workspace_id": workspace_id,
            "title": f"AI needs clarification: {task.get('title')}",
            "description": "Assigned AI agent requested clarifications before completing this task.",
            "severity": "high",
            "status": "open",
            "created_at": STORE.now_iso(),
            "target_user_id": task.get("assignee_user_id"),
            "kind": "agent_clarification",
            "task_id": task_id,
            "created_by": "system",
        }
        STORE.workspace_actions_required[workspace_id].append(action)
        EVENT_BUS.publish("workspace.action_required.created", workspace_id, {"action_id": action["id"]})


def _upsert_action_required_for_task(
    workspace_id: str,
    task: dict[str, object],
    *,
    kind: str,
    title: str,
    description: str,
    severity: str = "medium",
) -> None:
    target_user_id = task.get("assignee_user_id")
    if not isinstance(target_user_id, str) or not target_user_id:
        return

    actions = STORE.workspace_actions_required.setdefault(workspace_id, [])
    existing = next(
        (
            item
            for item in actions
            if str(item.get("kind")) == kind
            and str(item.get("task_id")) == str(task["id"])
            and str(item.get("target_user_id")) == target_user_id
            and str(item.get("status")) != "done"
        ),
        None,
    )
    if existing is not None:
        existing["title"] = title
        existing["description"] = description
        existing["severity"] = severity
        existing["status"] = "open"
        EVENT_BUS.publish(
            "workspace.action_required.updated",
            workspace_id,
            {"action_id": existing["id"], "status": "open"},
        )
        return

    action = {
        "id": STORE.new_id(),
        "workspace_id": workspace_id,
        "title": title,
        "description": description,
        "severity": severity,
        "status": "open",
        "created_at": STORE.now_iso(),
        "target_user_id": target_user_id,
        "kind": kind,
        "task_id": str(task["id"]),
        "created_by": "system",
    }
    actions.append(action)
    EVENT_BUS.publish("workspace.action_required.created", workspace_id, {"action_id": action["id"]})


@router.post("", response_model=TaskOut)
async def create_task(
    payload: TaskCreateIn,
    background_tasks: BackgroundTasks,
    user: dict[str, object] = Depends(get_current_user),
) -> TaskOut:
    require_workspace_member(payload.workspace_id, str(user["id"]))
    status_keys = _workspace_status_keys(payload.workspace_id)
    selected_status = payload.status.strip().lower().replace(" ", "_")
    if status_keys and selected_status not in status_keys:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown task status")
    task_id = STORE.new_id()
    now = STORE.now_iso()
    record: dict[str, object] = {
        "id": task_id,
        "workspace_id": payload.workspace_id,
        "project_id": payload.project_id,
        "title": payload.title,
        "description": payload.description,
        "status": selected_status or "todo",
        "priority": payload.priority.value,
        "acceptance_criteria": payload.acceptance_criteria,
        "assignee_user_id": payload.assignee_user_id,
        "assignee_agent_role": payload.assignee_agent_role,
        "proof_exempt": False,
        "created_at": now,
        "updated_at": now,
    }
    STORE.tasks[task_id] = record
    if record.get("assignee_user_id"):
        _upsert_action_required_for_task(
            payload.workspace_id,
            record,
            kind="task_assigned",
            title=f"Task assigned: {record['title']}",
            description="You were assigned as executor.",
            severity="medium",
        )
    if str(record.get("status")) == "review":
        _upsert_action_required_for_task(
            payload.workspace_id,
            record,
            kind="task_review_needed",
            title=f"Review required: {record['title']}",
            description="Task entered review status and requires your decision.",
            severity="high",
        )
    if record.get("assignee_agent_role"):
        background_tasks.add_task(
            _run_assigned_agent,
            payload.workspace_id,
            task_id,
            str(record["assignee_agent_role"]),
            "task_created",
        )
    EVENT_BUS.publish("task.created", payload.workspace_id, {"task_id": task_id})
    create_audit(payload.workspace_id, "user", str(user["id"]), "task.create", "task", task_id, payload.model_dump())
    return _task_out(record)


@router.get("", response_model=list[TaskOut])
def list_tasks(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[TaskOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    tasks = [task for task in STORE.tasks.values() if task["workspace_id"] == workspace_id]
    return [_task_out(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, user: dict[str, object] = Depends(get_current_user)) -> TaskOut:
    task = STORE.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    require_workspace_member(str(task["workspace_id"]), str(user["id"]))
    return _task_out(task)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    payload: TaskUpdateIn,
    background_tasks: BackgroundTasks,
    user: dict[str, object] = Depends(get_current_user),
) -> TaskOut:
    task = STORE.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    workspace_id = str(task["workspace_id"])
    require_workspace_member(workspace_id, str(user["id"]))

    if payload.status is not None:
        new_status = payload.status.strip().lower().replace(" ", "_")
        status_keys = _workspace_status_keys(workspace_id)
        if status_keys and new_status not in status_keys:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown task status")
    if payload.status == "done":
        artifact_exists = any(artifact.get("task_id") == task_id for artifact in STORE.artifacts.values())
        proof_exempt = payload.proof_exempt if payload.proof_exempt is not None else bool(task["proof_exempt"])
        if not artifact_exists and not proof_exempt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task requires proof-of-work artifact before marking done",
            )

    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "status":
            task[field] = str(value).strip().lower().replace(" ", "_")
        elif field == "priority":
            task[field] = value.value if hasattr(value, "value") else value
        else:
            task[field] = value

    task["updated_at"] = STORE.now_iso()
    if task.get("assignee_user_id"):
        _upsert_action_required_for_task(
            workspace_id,
            task,
            kind="task_assigned",
            title=f"Task assigned: {task['title']}",
            description="You were assigned as executor.",
            severity="medium",
        )
    if str(task.get("status")) == "review":
        _upsert_action_required_for_task(
            workspace_id,
            task,
            kind="task_review_needed",
            title=f"Review required: {task['title']}",
            description="Task entered review status and requires your decision.",
            severity="high",
        )
    role_key = str(task.get("assignee_agent_role") or "").strip()
    if role_key and (
        payload.assignee_agent_role is not None
        or payload.status is not None
        or payload.description is not None
        or payload.acceptance_criteria is not None
    ):
        background_tasks.add_task(
            _run_assigned_agent,
            workspace_id,
            task_id,
            role_key,
            "task_updated",
        )
    EVENT_BUS.publish("task.updated", workspace_id, {"task_id": task_id, "fields": payload.model_dump(exclude_none=True)})
    create_audit(workspace_id, "user", str(user["id"]), "task.update", "task", task_id, payload.model_dump(exclude_none=True))
    return _task_out(task)


@router.post("/{task_id}/dependencies", response_model=ActivityItem)
def add_dependency(
    task_id: str,
    payload: DependencyCreateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> ActivityItem:
    task = STORE.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    depends_on = STORE.tasks.get(payload.depends_on_task_id)
    if depends_on is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependency task not found")
    workspace_id = str(task["workspace_id"])
    require_workspace_member(workspace_id, str(user["id"]))

    if _has_cycle(task_id, payload.depends_on_task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dependency cycle detected")

    STORE.task_dependencies[task_id].add(payload.depends_on_task_id)
    EVENT_BUS.publish("task.dependency.added", workspace_id, {"task_id": task_id, "depends_on": payload.depends_on_task_id})
    now = datetime.fromisoformat(STORE.now_iso())
    return ActivityItem(
        id=STORE.new_id(),
        type="dependency_added",
        content=f"Task depends on {payload.depends_on_task_id}",
        created_at=now,
    )


@router.get("/{task_id}/activity", response_model=list[ActivityItem])
def task_activity(task_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[ActivityItem]:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))
    logs = [log for log in STORE.audit_logs if log.get("entity_type") == "task" and log.get("entity_id") == task_id]
    return [
        ActivityItem(
            id=str(log["id"]),
            type=str(log["action"]),
            content=str(log.get("payload", {})),
            created_at=datetime.fromisoformat(str(log["created_at"])),
        )
        for log in logs
    ]


@router.get("/{task_id}/agent-timeline", response_model=list[TaskAgentTimelineOut])
def task_agent_timeline(task_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[TaskAgentTimelineOut]:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))

    run_ids = [
        str(run["id"])
        for run in STORE.agent_runs.values()
        if run.get("task_id") == task_id and str(run.get("workspace_id")) == workspace_id and "role_key" in run
    ]
    timeline_items: list[dict[str, object]] = []
    for run_id in run_ids:
        timeline_items.extend(STORE.agent_run_timelines.get(run_id, []))

    ordered = sorted(timeline_items, key=lambda item: str(item.get("created_at", "")))
    return [_task_timeline_out(item) for item in ordered]


@router.post("/{task_id}/agent-revision", response_model=AgentRunOut)
async def request_agent_revision(
    task_id: str,
    payload: TaskAgentRevisionIn,
    user: dict[str, object] = Depends(get_current_user),
) -> AgentRunOut:
    task = STORE.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    workspace_id = str(task["workspace_id"])
    require_workspace_member(workspace_id, str(user["id"]))
    role_key = str(task.get("assignee_agent_role") or "").strip()
    if not role_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not assigned to an AI agent")

    request = AgentRunCreateIn(
        workspace_id=workspace_id,
        task_id=task_id,
        role_key=role_key,
        goal=(
            f"Revise current task output based on reviewer feedback.\n"
            f"Task: {task.get('title')}\n"
            f"Feedback: {payload.instruction.strip()}\n"
            "Return updated plan and completion checklist."
        ),
        stakes_level=payload.stakes_level,
    )
    run = await ORCHESTRATOR_SERVICE.execute(request)
    EVENT_BUS.publish("task.agent_revision.requested", workspace_id, {"task_id": task_id, "run_id": run["id"]})
    return _agent_run_out(run)


@router.get("/{task_id}/subtasks", response_model=list[TaskSubtaskOut])
def list_subtasks(task_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[TaskSubtaskOut]:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))
    items = _normalize_subtask_order(task_id)
    return [_task_subtask_out(item) for item in items]


@router.post("/{task_id}/subtasks", response_model=list[TaskSubtaskOut])
def create_subtask(
    task_id: str,
    payload: TaskSubtaskCreateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> list[TaskSubtaskOut]:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))
    items = STORE.task_subtasks.setdefault(task_id, [])
    order = payload.order if payload.order is not None else len(items)
    now = STORE.now_iso()
    subtask = {
        "id": STORE.new_id(),
        "task_id": task_id,
        "workspace_id": workspace_id,
        "title": payload.title.strip(),
        "description": payload.description.strip() if isinstance(payload.description, str) else None,
        "status": "todo",
        "order": order,
        "assignee_user_id": payload.assignee_user_id,
        "assignee_agent_role": payload.assignee_agent_role,
        "created_at": now,
        "updated_at": now,
    }
    items.append(subtask)
    normalized = _normalize_subtask_order(task_id)
    EVENT_BUS.publish("task.subtask.created", workspace_id, {"task_id": task_id, "subtask_id": subtask["id"]})
    return [_task_subtask_out(item) for item in normalized]


@router.patch("/{task_id}/subtasks/{subtask_id}", response_model=list[TaskSubtaskOut])
def update_subtask(
    task_id: str,
    subtask_id: str,
    payload: TaskSubtaskUpdateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> list[TaskSubtaskOut]:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))
    items = STORE.task_subtasks.setdefault(task_id, [])
    target = next((item for item in items if str(item["id"]) == subtask_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtask not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        target[field] = value
    target["updated_at"] = STORE.now_iso()
    normalized = _normalize_subtask_order(task_id)
    EVENT_BUS.publish("task.subtask.updated", workspace_id, {"task_id": task_id, "subtask_id": subtask_id})
    return [_task_subtask_out(item) for item in normalized]


@router.delete("/{task_id}/subtasks/{subtask_id}", response_model=list[TaskSubtaskOut])
def delete_subtask(
    task_id: str,
    subtask_id: str,
    user: dict[str, object] = Depends(get_current_user),
) -> list[TaskSubtaskOut]:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))
    items = STORE.task_subtasks.setdefault(task_id, [])
    if not any(str(item["id"]) == subtask_id for item in items):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtask not found")
    STORE.task_subtasks[task_id] = [item for item in items if str(item["id"]) != subtask_id]
    normalized = _normalize_subtask_order(task_id)
    EVENT_BUS.publish("task.subtask.deleted", workspace_id, {"task_id": task_id, "subtask_id": subtask_id})
    return [_task_subtask_out(item) for item in normalized]


@router.get("/{task_id}/proof-check", response_model=ProofCheckOut)
def proof_check(task_id: str, user: dict[str, object] = Depends(get_current_user)) -> ProofCheckOut:
    workspace_id = _get_workspace_id_for_task(task_id)
    task = STORE.tasks[task_id]
    require_workspace_member(workspace_id, str(user["id"]))
    has_artifact = any(artifact.get("task_id") == task_id for artifact in STORE.artifacts.values())
    proof_exempt = bool(task.get("proof_exempt", False))
    return ProofCheckOut(
        task_id=task_id,
        has_artifact=has_artifact,
        proof_exempt=proof_exempt,
        can_mark_done=has_artifact or proof_exempt,
    )


@router.post("/{task_id}/comments", response_model=TaskCommentOut)
def add_comment(
    task_id: str,
    payload: TaskCommentCreateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> TaskCommentOut:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))
    comment = {
        "id": STORE.new_id(),
        "task_id": task_id,
        "author_user_id": str(user["id"]),
        "author_username": str(user["username"]),
        "content": payload.content,
        "created_at": STORE.now_iso(),
    }
    STORE.task_comments[task_id].append(comment)
    EVENT_BUS.publish("task.comment.created", workspace_id, {"task_id": task_id, "comment_id": comment["id"]})
    return TaskCommentOut(
        id=str(comment["id"]),
        task_id=task_id,
        author_user_id=str(comment["author_user_id"]),
        author_username=str(comment["author_username"]),
        content=str(comment["content"]),
        created_at=datetime.fromisoformat(str(comment["created_at"])),
    )


@router.get("/{task_id}/comments", response_model=list[TaskCommentOut])
def list_comments(task_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[TaskCommentOut]:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))
    return [
        TaskCommentOut(
            id=str(comment["id"]),
            task_id=task_id,
            author_user_id=str(comment["author_user_id"]),
            author_username=str(comment["author_username"]),
            content=str(comment["content"]),
            created_at=datetime.fromisoformat(str(comment["created_at"])),
        )
        for comment in STORE.task_comments.get(task_id, [])
    ]


@router.post("/{task_id}/attachments", response_model=TaskAttachmentOut)
def add_attachment(
    task_id: str,
    payload: TaskAttachmentCreateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> TaskAttachmentOut:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))
    attachment = {
        "id": STORE.new_id(),
        "task_id": task_id,
        "author_user_id": str(user["id"]),
        "author_username": str(user["username"]),
        "file_name": payload.file_name,
        "url": payload.url,
        "mime_type": payload.mime_type,
        "created_at": STORE.now_iso(),
    }
    STORE.task_attachments[task_id].append(attachment)
    EVENT_BUS.publish("task.attachment.created", workspace_id, {"task_id": task_id, "attachment_id": attachment["id"]})
    return TaskAttachmentOut(
        id=str(attachment["id"]),
        task_id=task_id,
        author_user_id=str(attachment["author_user_id"]),
        author_username=str(attachment["author_username"]),
        file_name=str(attachment["file_name"]),
        url=str(attachment["url"]),
        mime_type=attachment.get("mime_type"),
        created_at=datetime.fromisoformat(str(attachment["created_at"])),
    )


@router.get("/{task_id}/attachments", response_model=list[TaskAttachmentOut])
def list_attachments(task_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[TaskAttachmentOut]:
    workspace_id = _get_workspace_id_for_task(task_id)
    require_workspace_member(workspace_id, str(user["id"]))
    return [
        TaskAttachmentOut(
            id=str(attachment["id"]),
            task_id=task_id,
            author_user_id=str(attachment["author_user_id"]),
            author_username=str(attachment["author_username"]),
            file_name=str(attachment["file_name"]),
            url=str(attachment["url"]),
            mime_type=attachment.get("mime_type"),
            created_at=datetime.fromisoformat(str(attachment["created_at"])),
        )
        for attachment in STORE.task_attachments.get(task_id, [])
    ]
