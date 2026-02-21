from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_workspace_member
from app.core.store import STORE
from app.domain.schemas import ArtifactCreateIn, ArtifactOut, ArtifactUpdateIn
from app.services.agents.document_generator import DocumentGenerator
from app.services.orchestration.approval import create_audit
from app.services.orchestration.event_bus import EVENT_BUS

router = APIRouter(prefix="/artifacts", tags=["artifacts"])
document_generator = DocumentGenerator()


@router.post("", response_model=ArtifactOut)
def create_artifact(payload: ArtifactCreateIn, user: dict[str, object] = Depends(get_current_user)) -> ArtifactOut:
    require_workspace_member(payload.workspace_id, str(user["id"]))
    artifact_id = STORE.new_id()
    record = {
        "id": artifact_id,
        "workspace_id": payload.workspace_id,
        "task_id": payload.task_id,
        "type": payload.type.value,
        "title": payload.title,
        "content": payload.content,
        "metadata": payload.metadata,
        "created_at": STORE.now_iso(),
    }
    STORE.artifacts[artifact_id] = record
    EVENT_BUS.publish("artifact.created", payload.workspace_id, {"artifact_id": artifact_id})
    create_audit(payload.workspace_id, "user", str(user["id"]), "artifact.create", "artifact", artifact_id, record)
    return ArtifactOut(
        id=artifact_id,
        workspace_id=payload.workspace_id,
        task_id=payload.task_id,
        type=payload.type,
        title=payload.title,
        content=payload.content,
        metadata=payload.metadata,
        created_at=datetime.fromisoformat(str(record["created_at"])),
    )


@router.get("", response_model=list[ArtifactOut])
def list_artifacts(workspace_id: str, user: dict[str, object] = Depends(get_current_user)) -> list[ArtifactOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    artifacts = [artifact for artifact in STORE.artifacts.values() if artifact["workspace_id"] == workspace_id]
    return [
        ArtifactOut(
            id=str(a["id"]),
            workspace_id=str(a["workspace_id"]),
            task_id=a.get("task_id"),
            type=str(a["type"]),
            title=str(a["title"]),
            content=str(a["content"]),
            metadata=dict(a.get("metadata", {})),
            created_at=datetime.fromisoformat(str(a["created_at"])),
        )
        for a in artifacts
    ]


@router.get("/{artifact_id}", response_model=ArtifactOut)
def get_artifact(artifact_id: str, user: dict[str, object] = Depends(get_current_user)) -> ArtifactOut:
    artifact = STORE.artifacts.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    require_workspace_member(str(artifact["workspace_id"]), str(user["id"]))
    return ArtifactOut(
        id=str(artifact["id"]),
        workspace_id=str(artifact["workspace_id"]),
        task_id=artifact.get("task_id"),
        type=str(artifact["type"]),
        title=str(artifact["title"]),
        content=str(artifact["content"]),
        metadata=dict(artifact.get("metadata", {})),
        created_at=datetime.fromisoformat(str(artifact["created_at"])),
    )


@router.put("/{artifact_id}", response_model=ArtifactOut)
def update_artifact(
    artifact_id: str,
    payload: ArtifactUpdateIn,
    user: dict[str, object] = Depends(get_current_user),
) -> ArtifactOut:
    """Update an existing artifact (title, content, metadata)."""
    artifact = STORE.artifacts.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    require_workspace_member(str(artifact["workspace_id"]), str(user["id"]))

    if payload.title is not None:
        artifact["title"] = payload.title
    if payload.content is not None:
        artifact["content"] = payload.content
    if payload.metadata is not None:
        artifact["metadata"] = payload.metadata
    artifact["updated_at"] = STORE.now_iso()

    create_audit(
        str(artifact["workspace_id"]),
        "user",
        str(user["id"]),
        "artifact.update",
        "artifact",
        artifact_id,
        artifact,
    )
    EVENT_BUS.publish("artifact.updated", str(artifact["workspace_id"]), {"artifact_id": artifact_id})

    return ArtifactOut(
        id=str(artifact["id"]),
        workspace_id=str(artifact["workspace_id"]),
        task_id=artifact.get("task_id"),
        type=str(artifact["type"]),
        title=str(artifact["title"]),
        content=str(artifact["content"]),
        metadata=dict(artifact.get("metadata", {})),
        created_at=datetime.fromisoformat(str(artifact["created_at"])),
    )


@router.post("/{artifact_id}/generate-document", response_model=ArtifactOut)
async def generate_document_from_artifact(
    artifact_id: str,
    user: dict[str, object] = Depends(get_current_user),
) -> ArtifactOut:
    """Generate a formatted Markdown document from an artifact."""
    artifact = STORE.artifacts.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    require_workspace_member(str(artifact["workspace_id"]), str(user["id"]))

    document_content = await document_generator.generate_markdown(
        title=str(artifact["title"]),
        content=str(artifact["content"]),
        artifact_type=str(artifact["type"]),
        metadata=dict(artifact.get("metadata", {})),
    )

    artifact["content"] = document_content
    artifact["metadata"] = dict(artifact.get("metadata", {}))
    artifact["metadata"]["format"] = "markdown"
    artifact["metadata"]["generated_at"] = STORE.now_iso()
    artifact["updated_at"] = STORE.now_iso()

    return ArtifactOut(
        id=str(artifact["id"]),
        workspace_id=str(artifact["workspace_id"]),
        task_id=artifact.get("task_id"),
        type=str(artifact["type"]),
        title=str(artifact["title"]),
        content=str(artifact["content"]),
        metadata=dict(artifact.get("metadata", {})),
        created_at=datetime.fromisoformat(str(artifact["created_at"])),
    )


@router.get("/{artifact_id}/export/markdown")
async def export_artifact_as_markdown(
    artifact_id: str,
    user: dict[str, object] = Depends(get_current_user),
):
    """Export artifact as Markdown file download."""
    from fastapi.responses import Response

    artifact = STORE.artifacts.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    require_workspace_member(str(artifact["workspace_id"]), str(user["id"]))

    title_slug = str(artifact["title"]).lower().replace(" ", "-").replace("/", "-")[:50]
    markdown_content = await document_generator.generate_markdown(
        title=str(artifact["title"]),
        content=str(artifact["content"]),
        artifact_type=str(artifact["type"]),
        metadata=dict(artifact.get("metadata", {})),
    )

    return Response(
        content=markdown_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{title_slug}.md"',
        },
    )


@router.post("/agent-runs/{run_id}/generate-document", response_model=ArtifactOut)
async def generate_document_from_agent_run(
    run_id: str,
    workspace_id: str,
    title: str | None = None,
    user: dict[str, object] = Depends(get_current_user),
) -> ArtifactOut:
    """Generate a Markdown document from an agent run output."""
    require_workspace_member(workspace_id, str(user["id"]))

    run = STORE.agent_runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")

    output = run.get("output", {})
    if not output:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent run has no output to generate document from",
        )

    document_title = title or f"Agent Output - {run.get('role_key', 'Unknown')}"
    document_content = await document_generator.generate_from_agent_output(
        role_key=str(run.get("role_key", "")),
        output=dict(output),
        title=document_title,
    )

    artifact_id = STORE.new_id()
    record = {
        "id": artifact_id,
        "workspace_id": workspace_id,
        "task_id": run.get("task_id"),
        "type": "report",
        "title": document_title,
        "content": document_content,
        "metadata": {
            "format": "markdown",
            "source_run_id": run_id,
            "generated_at": STORE.now_iso(),
        },
        "created_at": STORE.now_iso(),
    }
    STORE.artifacts[artifact_id] = record

    create_audit(
        workspace_id,
        "user",
        str(user["id"]),
        "artifact.create_from_agent_run",
        "artifact",
        artifact_id,
        record,
    )
    EVENT_BUS.publish("artifact.created", workspace_id, {"artifact_id": artifact_id})

    return ArtifactOut(
        id=artifact_id,
        workspace_id=workspace_id,
        task_id=run.get("task_id"),
        type="report",
        title=document_title,
        content=document_content,
        metadata=dict(record.get("metadata", {})),
        created_at=datetime.fromisoformat(str(record["created_at"])),
    )
