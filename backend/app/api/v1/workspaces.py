from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.v1.agents import DEFAULT_AGENT_PROFILES
from app.core.config import get_settings
from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import (
    ActionRequiredOut,
    ActionRequiredUpdateIn,
    APIMessage,
    FileProcessingStatus,
    TaskStatusCreateIn,
    TaskStatusOut,
    TaskStatusUpdateIn,
    WorkspaceAgentBulkCreateIn,
    WorkspaceAgentCreateIn,
    WorkspaceAgentOut,
    WorkspaceAgentUpdateIn,
    WorkspaceCreateIn,
    WorkspaceFileCreateIn,
    WorkspaceFileOut,
    WorkspaceInviteOut,
    WorkspaceMemberOut,
    WorkspaceOut,
    WorkspaceProfileOut,
    WorkspaceProfileUpdateIn,
    WorkspaceSettingsUpdateIn,
)
from app.services.memory.team_cortex import TEAM_CORTEX
from app.services.orchestration.event_bus import EVENT_BUS
from app.services.retrieval.file_text import (
    ALLOWED_EXTENSIONS,
    extract_text_from_file,
    normalize_extension,
)
from app.services.storage.minio_store import MINIO_STORE

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

ROLE_DEFAULTS = {role["key"]: role for role in DEFAULT_AGENT_PROFILES}
DEFAULT_TASK_STATUSES = [
    {"key": "todo", "label": "To do", "order": 0, "is_default": True},
    {"key": "in_progress", "label": "In progress", "order": 1, "is_default": False},
    {"key": "review", "label": "Review", "order": 2, "is_default": False},
    {"key": "done", "label": "Done", "order": 3, "is_default": False},
]


def _workspace_agent_out(agent: dict[str, object]) -> WorkspaceAgentOut:
    return WorkspaceAgentOut(
        id=str(agent["id"]),
        workspace_id=str(agent["workspace_id"]),
        role_key=str(agent["role_key"]),
        full_name=str(agent["full_name"]),
        system_prompt=str(agent["system_prompt"]),
        tone=str(agent["tone"]),
        character=str(agent["character"]),
        avatar_key=str(agent["avatar_key"]),
        status=str(agent["status"]),
        created_at=datetime.fromisoformat(str(agent["created_at"])),
    )


def _workspace_out(workspace_id: str, workspace: dict[str, object]) -> WorkspaceOut:
    return WorkspaceOut(
        id=workspace_id,
        name=str(workspace["name"]),
        slug=str(workspace["slug"]),
        description=workspace.get("description"),
        template=workspace.get("template"),
        invite_token=workspace.get("invite_token"),
        created_at=datetime.fromisoformat(str(workspace["created_at"])),
    )


def _member_profile(workspace_id: str, user_id: str) -> dict[str, object] | None:
    return STORE.workspace_member_profiles.get(workspace_id, {}).get(user_id)


def _create_workspace_agent(workspace_id: str, payload: WorkspaceAgentCreateIn) -> WorkspaceAgentOut:
    defaults = ROLE_DEFAULTS.get(payload.role_key)
    if defaults is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported role: {payload.role_key}")

    agent = {
        "id": STORE.new_id(),
        "workspace_id": workspace_id,
        "role_key": payload.role_key,
        "full_name": payload.full_name or defaults["display_name"],
        "system_prompt": payload.system_prompt or defaults["system_prompt"],
        "tone": payload.tone or defaults["tone"],
        "character": payload.character or defaults["character"],
        "avatar_key": payload.avatar_key or defaults["avatar_key"],
        "status": payload.status,
        "created_at": STORE.now_iso(),
        "x": float(10 + len(STORE.workspace_agents[workspace_id]) * 8),
        "y": float(58),
    }
    STORE.workspace_agents[workspace_id].append(agent)
    EVENT_BUS.publish("workspace.agent.created", workspace_id, {"agent_id": agent["id"], "role_key": payload.role_key})
    return _workspace_agent_out(agent)


def _require_admin(workspace_id: str, user_id: str) -> dict[str, object]:
    member = require_workspace_member(workspace_id, user_id)
    if member["role"] not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return member


def _workspace_invite_url(token: str) -> str:
    base = get_settings().frontend_base_url.rstrip("/")
    return f"{base}/invite/{token}"


def _initial_status_key(workspace_id: str) -> str:
    statuses = STORE.workspace_task_statuses.get(workspace_id) or DEFAULT_TASK_STATUSES
    defaults = [item for item in statuses if bool(item.get("is_default"))]
    if defaults:
        return str(defaults[0]["key"])
    return str(statuses[0]["key"])


@router.post("", response_model=WorkspaceOut)
def create_workspace(payload: WorkspaceCreateIn, user: dict[str, object] = Depends(get_current_user)) -> WorkspaceOut:
    workspace_id = STORE.new_id()
    invite_token = uuid4().hex[:16]
    record = {
        "id": workspace_id,
        "name": payload.name,
        "slug": payload.slug,
        "description": payload.description,
        "template": payload.template,
        "invite_token": invite_token,
        "created_at": STORE.now_iso(),
    }
    STORE.workspaces[workspace_id] = record
    STORE.workspace_members[workspace_id].append(
        {"workspace_id": workspace_id, "user_id": str(user["id"]), "role": "owner"}
    )
    STORE.workspace_member_profiles[workspace_id][str(user["id"])] = {
        "nickname": str(user["username"]),
        "avatar_key": "char1",
        "updated_at": STORE.now_iso(),
    }
    STORE.workspace_invites[invite_token] = {
        "workspace_id": workspace_id,
        "created_by": str(user["id"]),
        "created_at": STORE.now_iso(),
        "revoked": False,
    }
    STORE.workspace_task_statuses[workspace_id] = [dict(item) for item in DEFAULT_TASK_STATUSES]
    EVENT_BUS.publish("workspace.created", workspace_id, {"workspace_id": workspace_id})
    return _workspace_out(workspace_id, record)


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(user: dict[str, object] = Depends(get_current_user)) -> list[WorkspaceOut]:
    user_id = str(user["id"])
    workspace_ids = [
        str(member["workspace_id"])
        for members in STORE.workspace_members.values()
        for member in members
        if str(member["user_id"]) == user_id
    ]
    out: list[WorkspaceOut] = []
    for workspace_id in workspace_ids:
        workspace = STORE.workspaces.get(workspace_id)
        if workspace is None:
            continue
        out.append(_workspace_out(workspace_id, workspace))
    return out


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> WorkspaceOut:
    require_workspace_member(workspace_id, str(user["id"]))
    workspace = STORE.workspaces.get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return _workspace_out(workspace_id, workspace)


@router.patch("/{workspace_id}/settings", response_model=WorkspaceOut)
def update_workspace_settings(
    workspace_id: str,
    payload: WorkspaceSettingsUpdateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> WorkspaceOut:
    _require_admin(workspace_id, str(user["id"]))
    workspace = STORE.workspaces.get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        workspace[field] = value
    return _workspace_out(workspace_id, workspace)


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberOut])
def list_members(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[WorkspaceMemberOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    members = STORE.workspace_members.get(workspace_id, [])
    out: list[WorkspaceMemberOut] = []
    for member in members:
        member_user = STORE.users.get(str(member["user_id"]), {})
        profile = _member_profile(workspace_id, str(member["user_id"])) or {}
        out.append(
            WorkspaceMemberOut(
                workspace_id=str(member["workspace_id"]),
                user_id=str(member["user_id"]),
                role=str(member["role"]),
                username=str(member_user.get("username")) if member_user else None,
                nickname=str(profile.get("nickname")) if profile else None,
                avatar_key=str(profile.get("avatar_key")) if profile else None,
            )
        )
    return out


@router.delete("/{workspace_id}/members/{member_user_id}", response_model=APIMessage)
def remove_member(
    workspace_id: str,
    member_user_id: str,
    user: dict[str, object] = Depends(get_current_user),
) -> APIMessage:
    requester = _require_admin(workspace_id, str(user["id"]))
    if requester["role"] == "owner" and str(user["id"]) == member_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot remove self")

    members = STORE.workspace_members.get(workspace_id, [])
    target = next((member for member in members if str(member["user_id"]) == member_user_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if str(target["role"]) == "owner":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot be removed")

    STORE.workspace_members[workspace_id] = [member for member in members if str(member["user_id"]) != member_user_id]
    STORE.workspace_member_profiles.get(workspace_id, {}).pop(member_user_id, None)
    EVENT_BUS.publish("workspace.member.removed", workspace_id, {"user_id": member_user_id})
    return APIMessage(message="Member removed")


@router.patch("/{workspace_id}/me/profile", response_model=WorkspaceProfileOut)
def update_my_profile(
    workspace_id: str,
    payload: WorkspaceProfileUpdateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> WorkspaceProfileOut:
    require_workspace_member(workspace_id, str(user["id"]))
    now = STORE.now_iso()
    STORE.workspace_member_profiles[workspace_id][str(user["id"])] = {
        "nickname": payload.nickname.strip(),
        "avatar_key": payload.avatar_key.strip(),
        "updated_at": now,
    }
    EVENT_BUS.publish("workspace.member.profile.updated", workspace_id, {"user_id": str(user["id"])})
    return WorkspaceProfileOut(
        workspace_id=workspace_id,
        user_id=str(user["id"]),
        nickname=payload.nickname.strip(),
        avatar_key=payload.avatar_key.strip(),
        updated_at=datetime.fromisoformat(now),
    )


@router.get("/{workspace_id}/me/profile", response_model=WorkspaceProfileOut)
def get_my_profile(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> WorkspaceProfileOut:
    require_workspace_member(workspace_id, str(user["id"]))
    profile = _member_profile(workspace_id, str(user["id"]))
    if profile is None:
        profile = {
            "nickname": str(user["username"]),
            "avatar_key": "char1",
            "updated_at": STORE.now_iso(),
        }
        STORE.workspace_member_profiles[workspace_id][str(user["id"])] = profile
    return WorkspaceProfileOut(
        workspace_id=workspace_id,
        user_id=str(user["id"]),
        nickname=str(profile["nickname"]),
        avatar_key=str(profile["avatar_key"]),
        updated_at=datetime.fromisoformat(str(profile["updated_at"])),
    )


@router.get("/{workspace_id}/invite-link", response_model=WorkspaceInviteOut)
def get_invite_link(
    workspace_id: str, user: dict[str, object] = Depends(get_current_user)
) -> WorkspaceInviteOut:
    _require_admin(workspace_id, str(user["id"]))
    workspace = STORE.workspaces.get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    token = str(workspace["invite_token"])
    invite = STORE.workspace_invites.get(token)
    if invite is None:
        invite = {
            "workspace_id": workspace_id,
            "created_by": str(user["id"]),
            "created_at": STORE.now_iso(),
            "revoked": False,
        }
        STORE.workspace_invites[token] = invite
    return WorkspaceInviteOut(
        workspace_id=workspace_id,
        token=token,
        invite_url=_workspace_invite_url(token),
        created_at=datetime.fromisoformat(str(invite["created_at"])),
        revoked=bool(invite.get("revoked", False)),
    )


@router.post("/{workspace_id}/invite-link/refresh", response_model=WorkspaceInviteOut)
def refresh_invite_link(
    workspace_id: str, user: dict[str, object] = Depends(get_current_user)
) -> WorkspaceInviteOut:
    _require_admin(workspace_id, str(user["id"]))
    workspace = STORE.workspaces.get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    previous = workspace.get("invite_token")
    if isinstance(previous, str) and previous in STORE.workspace_invites:
        STORE.workspace_invites[previous]["revoked"] = True
    token = uuid4().hex[:16]
    workspace["invite_token"] = token
    STORE.workspace_invites[token] = {
        "workspace_id": workspace_id,
        "created_by": str(user["id"]),
        "created_at": STORE.now_iso(),
        "revoked": False,
    }
    return WorkspaceInviteOut(
        workspace_id=workspace_id,
        token=token,
        invite_url=_workspace_invite_url(token),
        created_at=datetime.fromisoformat(str(STORE.workspace_invites[token]["created_at"])),
        revoked=False,
    )


@router.get("/invitations/{token}", response_model=WorkspaceOut)
def get_invitation(token: str, user: dict[str, object] = Depends(get_current_user)) -> WorkspaceOut:
    _ = user
    invite = STORE.workspace_invites.get(token)
    if invite is None or bool(invite.get("revoked", False)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    workspace_id = str(invite["workspace_id"])
    workspace = STORE.workspaces.get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return _workspace_out(workspace_id, workspace)


@router.post("/invitations/{token}/accept", response_model=WorkspaceOut)
def accept_invitation(token: str, user: dict[str, object] = Depends(get_current_user)) -> WorkspaceOut:
    invite = STORE.workspace_invites.get(token)
    if invite is None or bool(invite.get("revoked", False)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    workspace_id = str(invite["workspace_id"])
    workspace = STORE.workspaces.get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    user_id = str(user["id"])
    members = STORE.workspace_members[workspace_id]
    if not any(str(member["user_id"]) == user_id for member in members):
        members.append({"workspace_id": workspace_id, "user_id": user_id, "role": "member"})
    if user_id not in STORE.workspace_member_profiles[workspace_id]:
        STORE.workspace_member_profiles[workspace_id][user_id] = {
            "nickname": str(user["username"]),
            "avatar_key": "char2",
            "updated_at": STORE.now_iso(),
        }
    EVENT_BUS.publish("workspace.member.joined", workspace_id, {"user_id": user_id})
    return _workspace_out(workspace_id, workspace)


@router.get("/{workspace_id}/task-statuses", response_model=list[TaskStatusOut])
def list_task_statuses(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[TaskStatusOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    statuses = STORE.workspace_task_statuses.get(workspace_id)
    if not statuses:
        statuses = [dict(item) for item in DEFAULT_TASK_STATUSES]
        STORE.workspace_task_statuses[workspace_id] = statuses
    return [TaskStatusOut(**status) for status in statuses]


@router.post("/{workspace_id}/task-statuses", response_model=list[TaskStatusOut])
def add_task_status(
    workspace_id: str,
    payload: TaskStatusCreateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> list[TaskStatusOut]:
    _require_admin(workspace_id, str(user["id"]))
    statuses = STORE.workspace_task_statuses.setdefault(workspace_id, [dict(item) for item in DEFAULT_TASK_STATUSES])
    key = payload.key.strip().lower().replace(" ", "_")
    if any(str(item["key"]) == key for item in statuses):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status key already exists")
    statuses.append({"key": key, "label": payload.label.strip(), "order": len(statuses), "is_default": False})
    EVENT_BUS.publish("workspace.task_status.created", workspace_id, {"key": key})
    return [TaskStatusOut(**item) for item in statuses]


@router.patch("/{workspace_id}/task-statuses/{status_key}", response_model=list[TaskStatusOut])
def update_task_status(
    workspace_id: str,
    status_key: str,
    payload: TaskStatusUpdateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> list[TaskStatusOut]:
    _require_admin(workspace_id, str(user["id"]))
    statuses = STORE.workspace_task_statuses.setdefault(workspace_id, [dict(item) for item in DEFAULT_TASK_STATUSES])
    target = next((item for item in statuses if str(item["key"]) == status_key), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")

    if payload.label is not None:
        target["label"] = payload.label.strip()

    if payload.order is not None:
        current_index = statuses.index(target)
        next_index = max(0, min(len(statuses) - 1, payload.order))
        statuses.pop(current_index)
        statuses.insert(next_index, target)
        for index, item in enumerate(statuses):
            item["order"] = index

    EVENT_BUS.publish("workspace.task_status.updated", workspace_id, {"key": status_key})
    return [TaskStatusOut(**item) for item in statuses]


@router.delete("/{workspace_id}/task-statuses/{status_key}", response_model=list[TaskStatusOut])
def remove_task_status(
    workspace_id: str,
    status_key: str,
    user: dict[str, object] = Depends(get_current_user),
) -> list[TaskStatusOut]:
    _require_admin(workspace_id, str(user["id"]))
    statuses = STORE.workspace_task_statuses.setdefault(workspace_id, [dict(item) for item in DEFAULT_TASK_STATUSES])
    target = next((item for item in statuses if str(item["key"]) == status_key), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
    if bool(target.get("is_default")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Default status cannot be removed")

    initial_key = _initial_status_key(workspace_id)
    for task in STORE.tasks.values():
        if str(task.get("workspace_id")) == workspace_id and str(task.get("status")) == status_key:
            task["status"] = initial_key
            task["updated_at"] = STORE.now_iso()

    STORE.workspace_task_statuses[workspace_id] = [item for item in statuses if str(item["key"]) != status_key]
    for index, item in enumerate(STORE.workspace_task_statuses[workspace_id]):
        item["order"] = index
    EVENT_BUS.publish("workspace.task_status.removed", workspace_id, {"key": status_key, "reassigned_to": initial_key})
    return [TaskStatusOut(**item) for item in STORE.workspace_task_statuses[workspace_id]]


@router.get("/{workspace_id}/files", response_model=list[WorkspaceFileOut])
def list_workspace_files(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[WorkspaceFileOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    return [
        WorkspaceFileOut(
            id=str(item["id"]),
            workspace_id=workspace_id,
            name=str(item["name"]),
            url=str(item["url"]),
            type=str(item["type"]),
            processing_status=FileProcessingStatus(item.get("processing_status", "completed")),
            processing_error=item.get("processing_error"),
            embedding_status=item.get("embedding_status"),
            uploaded_by_user_id=str(item["uploaded_by_user_id"]),
            created_at=datetime.fromisoformat(str(item["created_at"])),
            updated_at=datetime.fromisoformat(str(item["updated_at"])) if item.get("updated_at") else None,
        )
        for item in STORE.workspace_files.get(workspace_id, [])
    ]


@router.post("/{workspace_id}/files", response_model=WorkspaceFileOut)
def create_workspace_file(
    workspace_id: str,
    payload: WorkspaceFileCreateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> WorkspaceFileOut:
    _ = payload
    _ = user
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Use multipart upload endpoint /workspaces/{workspace_id}/files/upload",
    )


@router.post("/{workspace_id}/files/upload", response_model=WorkspaceFileOut)
async def upload_workspace_file(
    workspace_id: str,
    file: UploadFile = File(...),
    user: dict[str, object] = Depends(get_current_user),
) -> WorkspaceFileOut:
    require_workspace_member(workspace_id, str(user["id"]))
    filename = file.filename or "uploaded-file"
    extension = normalize_extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file type. Allowed: {allowed}")

    # Create file record with processing status
    file_id = STORE.new_id()
    item = {
        "id": file_id,
        "workspace_id": workspace_id,
        "name": filename,
        "url": "",
        "type": extension.replace(".", "") or "file",
        "processing_status": "uploading",
        "uploaded_by_user_id": str(user["id"]),
        "created_at": STORE.now_iso(),
        "updated_at": STORE.now_iso(),
        "object_key": None,
        "extracted_text": "",
    }
    STORE.workspace_files[workspace_id].append(item)

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")

        # Update status to processing
        item["processing_status"] = "processing"
        item["updated_at"] = STORE.now_iso()
        EVENT_BUS.publish("workspace.file.processing", workspace_id, {"file_id": file_id, "status": "processing"})

        # Extract text
        try:
            item["processing_status"] = "extracting_text"
            extracted_text = extract_text_from_file(filename, content)
            item["extracted_text"] = extracted_text
        except ValueError as exc:
            item["processing_status"] = "failed"
            item["processing_error"] = str(exc)
            item["updated_at"] = STORE.now_iso()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            item["processing_status"] = "failed"
            item["processing_error"] = "Could not parse uploaded file"
            item["updated_at"] = STORE.now_iso()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not parse uploaded file") from exc

        if not extracted_text.strip():
            item["processing_status"] = "failed"
            item["processing_error"] = "No extractable text found in file"
            item["updated_at"] = STORE.now_iso()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extractable text found in file",
            )

        # Upload to storage
        safe_name = Path(filename).name.replace(" ", "_")
        object_key = f"{workspace_id}/{uuid4().hex}-{safe_name}"
        try:
            file_url = MINIO_STORE.upload_bytes(
                object_key=object_key,
                content=content,
                content_type=file.content_type or "application/octet-stream",
            )
            item["url"] = file_url
            item["object_key"] = object_key
        except Exception as exc:
            item["processing_status"] = "failed"
            item["processing_error"] = "File storage unavailable"
            item["updated_at"] = STORE.now_iso()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="File storage unavailable") from exc

        # Add to RAG/embedding
        item["processing_status"] = "embedding"
        item["updated_at"] = STORE.now_iso()
        EVENT_BUS.publish("workspace.file.processing", workspace_id, {"file_id": file_id, "status": "embedding"})

        TEAM_CORTEX.add_evidence(
            workspace_id=workspace_id,
            task_id=None,
            run_id=None,
            claim=f"Uploaded file indexed: {filename}",
            source_type="workspace_file",
            source_ref=f"workspace_file:{file_id}",
            confidence=0.9,
        )

        # Mark as completed
        item["processing_status"] = "completed"
        item["embedding_status"] = "indexed"
        item["updated_at"] = STORE.now_iso()
        EVENT_BUS.publish("workspace.file.created", workspace_id, {"file_id": file_id})
        EVENT_BUS.publish("workspace.file.processing", workspace_id, {"file_id": file_id, "status": "completed"})

    except HTTPException:
        raise
    except Exception as exc:
        item["processing_status"] = "failed"
        item["processing_error"] = str(exc)
        item["updated_at"] = STORE.now_iso()
        raise

    return WorkspaceFileOut(
        id=str(item["id"]),
        workspace_id=workspace_id,
        name=str(item["name"]),
        url=str(item["url"]),
        type=str(item["type"]),
        processing_status=FileProcessingStatus(item["processing_status"]),
        processing_error=item.get("processing_error"),
        embedding_status=item.get("embedding_status"),
        uploaded_by_user_id=str(item["uploaded_by_user_id"]),
        created_at=datetime.fromisoformat(str(item["created_at"])),
        updated_at=datetime.fromisoformat(str(item["updated_at"])) if item.get("updated_at") else None,
    )


@router.get("/{workspace_id}/actions-required", response_model=list[ActionRequiredOut])
def list_actions_required(
    workspace_id: str, user: dict[str, object] = Depends(get_current_user)
) -> list[ActionRequiredOut]:
    member = require_workspace_member(workspace_id, str(user["id"]))
    user_id = str(user["id"])
    is_admin = str(member["role"]) in {"owner", "admin"}
    return [
        ActionRequiredOut(
            id=str(item["id"]),
            workspace_id=workspace_id,
            title=str(item["title"]),
            description=str(item["description"]),
            severity=str(item["severity"]),
            status=str(item["status"]),
            created_at=datetime.fromisoformat(str(item["created_at"])),
        )
        for item in STORE.workspace_actions_required.get(workspace_id, [])
        if is_admin or item.get("target_user_id") in {None, user_id}
    ]


@router.post("/{workspace_id}/actions-required", response_model=ActionRequiredOut)
def create_action_required(
    workspace_id: str,
    payload: dict[str, object],
    user: dict[str, object] = Depends(get_current_user),
) -> ActionRequiredOut:
    _ = workspace_id
    _ = payload
    _ = user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Actions required are system-generated by agent/runtime signals",
    )


@router.patch("/{workspace_id}/actions-required/{action_id}", response_model=ActionRequiredOut)
def update_action_required(
    workspace_id: str,
    action_id: str,
    payload: ActionRequiredUpdateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> ActionRequiredOut:
    member = require_workspace_member(workspace_id, str(user["id"]))
    user_id = str(user["id"])
    is_admin = str(member["role"]) in {"owner", "admin"}
    action = next(
        (item for item in STORE.workspace_actions_required.get(workspace_id, []) if str(item["id"]) == action_id), None
    )
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    target_user_id = action.get("target_user_id")
    if target_user_id and not is_admin and str(target_user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this action")
    action["status"] = payload.status
    EVENT_BUS.publish("workspace.action_required.updated", workspace_id, {"action_id": action_id, "status": payload.status})
    return ActionRequiredOut(
        id=str(action["id"]),
        workspace_id=workspace_id,
        title=str(action["title"]),
        description=str(action["description"]),
        severity=str(action["severity"]),
        status=str(action["status"]),
        created_at=datetime.fromisoformat(str(action["created_at"])),
    )


@router.get("/{workspace_id}/agents", response_model=list[WorkspaceAgentOut])
def list_workspace_agents(
    workspace_id: str, user: dict[str, object] = Depends(get_current_user)
) -> list[WorkspaceAgentOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    return [_workspace_agent_out(agent) for agent in STORE.workspace_agents.get(workspace_id, [])]


@router.post("/{workspace_id}/agents", response_model=WorkspaceAgentOut)
def create_workspace_agent(
    workspace_id: str,
    payload: WorkspaceAgentCreateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> WorkspaceAgentOut:
    _require_admin(workspace_id, str(user["id"]))
    return _create_workspace_agent(workspace_id, payload)


@router.post("/{workspace_id}/agents/bootstrap", response_model=list[WorkspaceAgentOut])
def bootstrap_workspace_agents(
    workspace_id: str,
    payload: WorkspaceAgentBulkCreateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> list[WorkspaceAgentOut]:
    _require_admin(workspace_id, str(user["id"]))
    if STORE.workspace_agents.get(workspace_id):
        return [_workspace_agent_out(agent) for agent in STORE.workspace_agents[workspace_id]]
    created: list[WorkspaceAgentOut] = []
    for agent_payload in payload.agents:
        created.append(_create_workspace_agent(workspace_id, agent_payload))
    return created


@router.patch("/{workspace_id}/agents/{agent_id}", response_model=WorkspaceAgentOut)
def update_workspace_agent(
    workspace_id: str,
    agent_id: str,
    payload: WorkspaceAgentUpdateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> WorkspaceAgentOut:
    _require_admin(workspace_id, str(user["id"]))
    agents = STORE.workspace_agents.get(workspace_id, [])
    target = next((agent for agent in agents if str(agent["id"]) == agent_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        target[field] = value
    EVENT_BUS.publish(
        "workspace.agent.updated", workspace_id, {"agent_id": agent_id, "fields": payload.model_dump(exclude_none=True)}
    )
    return _workspace_agent_out(target)


@router.delete("/{workspace_id}/agents/{agent_id}", response_model=APIMessage)
def delete_workspace_agent(
    workspace_id: str,
    agent_id: str,
    user: dict[str, object] = Depends(get_current_user),
) -> APIMessage:
    _require_admin(workspace_id, str(user["id"]))
    agents = STORE.workspace_agents.get(workspace_id, [])
    if not any(str(agent["id"]) == agent_id for agent in agents):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    STORE.workspace_agents[workspace_id] = [agent for agent in agents if str(agent["id"]) != agent_id]
    EVENT_BUS.publish("workspace.agent.deleted", workspace_id, {"agent_id": agent_id})
    return APIMessage(message="Agent deleted")
