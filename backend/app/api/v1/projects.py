from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import ProjectCreateIn, ProjectOut
from app.services.orchestration.event_bus import EVENT_BUS

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreateIn, user: dict[str, object] = Depends(get_current_user)) -> ProjectOut:
    require_workspace_member(payload.workspace_id, str(user["id"]))
    project_id = STORE.new_id()
    record = {
        "id": project_id,
        "workspace_id": payload.workspace_id,
        "name": payload.name,
        "description": payload.description,
        "created_at": STORE.now_iso(),
    }
    STORE.projects[project_id] = record
    EVENT_BUS.publish("project.created", payload.workspace_id, {"project_id": project_id})
    return ProjectOut(
        id=project_id,
        workspace_id=payload.workspace_id,
        name=payload.name,
        description=payload.description,
        created_at=datetime.fromisoformat(str(record["created_at"])),
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[ProjectOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    projects = [project for project in STORE.projects.values() if project["workspace_id"] == workspace_id]
    return [
        ProjectOut(
            id=str(project["id"]),
            workspace_id=str(project["workspace_id"]),
            name=str(project["name"]),
            description=project.get("description"),
            created_at=datetime.fromisoformat(str(project["created_at"])),
        )
        for project in projects
    ]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: dict[str, object] = Depends(get_current_user)) -> ProjectOut:
    project = STORE.projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    require_workspace_member(str(project["workspace_id"]), str(user["id"]))
    return ProjectOut(
        id=str(project["id"]),
        workspace_id=str(project["workspace_id"]),
        name=str(project["name"]),
        description=project.get("description"),
        created_at=datetime.fromisoformat(str(project["created_at"])),
    )
