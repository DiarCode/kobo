from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.dependencies import get_current_user, require_workspace_member
from app.domain.schemas import (
    AssistantChatIn,
    AssistantChatOut,
    AssistantHistoryItemOut,
    AssistantVoiceTokenOut,
)
from app.services.assistants.workspace_assistant import WORKSPACE_ASSISTANT

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/workspaces/{workspace_id}/history", response_model=list[AssistantHistoryItemOut])
def get_assistant_history(
    workspace_id: str,
    user: dict[str, object] = Depends(get_current_user),
) -> list[AssistantHistoryItemOut]:
    require_workspace_member(workspace_id, str(user["id"]))
    return [
        AssistantHistoryItemOut(
            id=str(item["id"]),
            workspace_id=str(item["workspace_id"]),
            user_id=str(item["user_id"]),
            role=str(item["role"]),
            content=str(item["content"]),
            created_at=datetime.fromisoformat(str(item["created_at"])),
            metadata=dict(item.get("metadata", {})),
        )
        for item in WORKSPACE_ASSISTANT.history(workspace_id)
    ]


@router.post("/workspaces/{workspace_id}/chat", response_model=AssistantChatOut)
async def assistant_chat(
    workspace_id: str,
    payload: AssistantChatIn,
    user: dict[str, object] = Depends(get_current_user),
) -> AssistantChatOut:
    require_workspace_member(workspace_id, str(user["id"]))
    message, used_context = await WORKSPACE_ASSISTANT.chat(
        workspace_id=workspace_id,
        user_id=str(user["id"]),
        username=str(user["username"]),
        message=payload.message,
        include_history=payload.include_history,
        task_id=payload.task_id,
    )
    metadata = dict(message.get("metadata", {}))
    return AssistantChatOut(
        message_id=str(message["id"]),
        workspace_id=workspace_id,
        response=str(message["content"]),
        used_context=used_context,
        model=str(metadata["model"]) if "model" in metadata else None,
        fallback_used=bool(metadata.get("fallback_used", False)),
        warning=str(metadata["warning"]) if "warning" in metadata and metadata["warning"] else None,
        created_at=datetime.fromisoformat(str(message["created_at"])),
    )


@router.post("/workspaces/{workspace_id}/chat/stream")
async def assistant_chat_stream(
    workspace_id: str,
    payload: AssistantChatIn,
    user: dict[str, object] = Depends(get_current_user),
):
    """Stream chat response with real-time tokens using Server-Sent Events."""
    require_workspace_member(workspace_id, str(user["id"]))

    async def generate():
        """Generate streaming response."""
        try:
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'message_id': 'streaming'})}\n\n"

            # Get workspace context
            from app.core.store import STORE
            from app.services.assistants.workspace_assistant import get_agent_service_client

            tasks = [task for task in STORE.tasks.values() if str(task.get("workspace_id")) == workspace_id]
            completed_tasks = [task for task in tasks if str(task.get("status")) == "done"][:6]
            open_tasks = [task for task in tasks if str(task.get("status")) != "done"][:8]
            files = STORE.workspace_files.get(workspace_id, [])[:8]
            artifacts = [item for item in STORE.artifacts.values() if str(item.get("workspace_id")) == workspace_id][:6]
            members = STORE.workspace_members.get(workspace_id, [])

            workspace_context = (
                "Workspace snapshot:\n"
                f"Members: {len(members)}\n"
                f"Open tasks: {len(open_tasks)}\n"
                f"Completed tasks: {len(completed_tasks)}\n"
                f"Files: {len(files)}\n"
                f"Artifacts: {len(artifacts)}\n"
            )

            # Build conversation history
            conversation_history = []
            for item in WORKSPACE_ASSISTANT._recent_history(workspace_id, limit=12):
                role = str(item.get("role"))
                content = str(item.get("content", "")).strip()
                if content:
                    conversation_history.append({"role": role, "content": content})

            # Build task context
            task_context = ""
            if payload.task_id and payload.task_id in STORE.tasks:
                task = STORE.tasks[payload.task_id]
                task_context = (
                    "\nFocused task:\n"
                    f"- title: {task.get('title')}\n"
                    f"- status: {task.get('status')}\n"
                    f"- description: {task.get('description') or 'n/a'}\n"
                )

            # Call agent service with streaming
            client = get_agent_service_client()
            stream_payload = {
                "message": payload.message,
                "workspace_context": workspace_context,
                "conversation_history": conversation_history if payload.include_history else [],
                "task_context": task_context,
                "stream": True,
            }

            # Make streaming request to agent service
            async with client.stream("POST", "/chat/complete/stream", json=stream_payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line + "\n"

        except Exception as e:
            import logging
            logging.error(f"Chat streaming failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/workspaces/{workspace_id}/voice/token", response_model=AssistantVoiceTokenOut)
def create_assistant_voice_token(
    workspace_id: str,
    user: dict[str, object] = Depends(get_current_user),
) -> AssistantVoiceTokenOut:
    require_workspace_member(workspace_id, str(user["id"]))
    settings = get_settings()
    identity = f"user-{user['id']}"
    token, room = WORKSPACE_ASSISTANT.livekit_token(
        workspace_id=workspace_id,
        identity=identity,
        display_name=str(user["username"]),
    )
    return AssistantVoiceTokenOut(
        workspace_id=workspace_id,
        identity=identity,
        room=room,
        token=token,
        livekit_url=settings.livekit_public_url,
    )
