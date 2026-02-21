from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from jose import jwt

from app.core.config import get_settings
from app.core.store import STORE

logger = logging.getLogger(__name__)

# Agent service client
_agent_service_client: httpx.AsyncClient | None = None


def get_agent_service_client() -> httpx.AsyncClient:
    """Get or create the agent service HTTP client."""
    global _agent_service_client
    if _agent_service_client is None:
        settings = get_settings()
        _agent_service_client = httpx.AsyncClient(
            base_url=settings.agent_service_url,
            timeout=120.0,
        )
    return _agent_service_client


@dataclass(slots=True)
class WorkspaceAssistantService:
    def _recent_history(self, workspace_id: str, limit: int = 12) -> list[dict[str, Any]]:
        return list(STORE.workspace_assistant_messages.get(workspace_id, []))[-limit:]

    def _workspace_context(self, workspace_id: str) -> tuple[list[str], str]:
        tasks = [task for task in STORE.tasks.values() if str(task.get("workspace_id")) == workspace_id]
        completed_tasks = [task for task in tasks if str(task.get("status")) == "done"][:6]
        open_tasks = [task for task in tasks if str(task.get("status")) != "done"][:8]
        files = STORE.workspace_files.get(workspace_id, [])[:8]
        artifacts = [item for item in STORE.artifacts.values() if str(item.get("workspace_id")) == workspace_id][:6]
        members = STORE.workspace_members.get(workspace_id, [])
        profiles = STORE.workspace_member_profiles.get(workspace_id, {})

        context_labels = [
            f"members:{len(members)}",
            f"tasks:{len(tasks)}",
            f"completed_tasks:{len(completed_tasks)}",
            f"files:{len(files)}",
            f"artifacts:{len(artifacts)}",
        ]

        member_lines: list[str] = []
        for member in members:
            user_id = str(member.get("user_id"))
            user = STORE.users.get(user_id)
            profile = profiles.get(user_id, {})
            member_lines.append(
                f"- {profile.get('nickname') or (user or {}).get('username') or user_id} ({member.get('role')})"
            )

        open_task_lines = [
            f"- [{task.get('status')}] {task.get('title')} (priority: {task.get('priority')})" for task in open_tasks
        ]
        done_task_lines = [f"- {task.get('title')}" for task in completed_tasks]
        file_lines = [
            f"- {item.get('name')}: {(str(item.get('extracted_text', ''))[:320]).replace(chr(10), ' ')}" for item in files
        ]
        artifact_lines = [f"- {item.get('type')}: {item.get('title')}" for item in artifacts]

        context = (
            "Workspace snapshot:\n"
            f"Members:\n{chr(10).join(member_lines) if member_lines else '- none'}\n"
            f"Open tasks:\n{chr(10).join(open_task_lines) if open_task_lines else '- none'}\n"
            f"Completed tasks:\n{chr(10).join(done_task_lines) if done_task_lines else '- none'}\n"
            f"Files:\n{chr(10).join(file_lines) if file_lines else '- none'}\n"
            f"Artifacts:\n{chr(10).join(artifact_lines) if artifact_lines else '- none'}\n"
        )
        return context_labels, context

    def _persist_message(
        self,
        workspace_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        item = {
            "id": STORE.new_id(),
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "created_at": STORE.now_iso(),
            "metadata": metadata or {},
        }
        STORE.workspace_assistant_messages[workspace_id].append(item)
        return item

    async def chat(
        self,
        *,
        workspace_id: str,
        user_id: str,
        username: str,
        message: str,
        include_history: bool,
        task_id: str | None = None,
    ) -> tuple[dict[str, Any], list[str]]:
        used_context, workspace_context = self._workspace_context(workspace_id)
        user_message = self._persist_message(
            workspace_id,
            user_id,
            "user",
            message,
            {"task_id": task_id},
        )

        conversation_history: list[dict[str, str]] = []
        if include_history:
            history_lines = []
            for item in self._recent_history(workspace_id, limit=12):
                role = str(item.get("role"))
                content = str(item.get("content", "")).strip()
                if not content:
                    continue
                history_lines.append(f"{role.upper()}: {content}")
                conversation_history.append({"role": role, "content": content})

        task_context = ""
        if task_id and task_id in STORE.tasks:
            task = STORE.tasks[task_id]
            task_context = (
                "\nFocused task:\n"
                f"- title: {task.get('title')}\n"
                f"- status: {task.get('status')}\n"
                f"- description: {task.get('description') or 'n/a'}\n"
            )
            used_context.append(f"task:{task_id}")

        # Use agent service for chat completion
        response_text = "Unknown."
        selected_model: str | None = None
        fallback_used = False
        warning: str | None = None
        model_errors: list[str] = []

        try:
            client = get_agent_service_client()
            payload = {
                "message": message,
                "workspace_context": workspace_context,
                "conversation_history": conversation_history,
                "task_context": task_context,
                "stream": False,
            }
            response = await client.post("/chat/complete", json=payload)
            response.raise_for_status()
            data = response.json()
            response_text = data.get("response", "Unknown.")
            selected_model = data.get("model_used")
            fallback_used = data.get("fallback_used", False)
            warning = data.get("warning")
        except Exception as error:
            model_errors.append(str(error))
            logger.warning("agent_service_chat_failed", extra={"error": str(error)})
            # Fallback response
            response_text = (
                "Assistant service unavailable right now. "
                f"Reason: {str(error)}. "
                "Try again in a moment."
            )

        assistant_message = self._persist_message(
            workspace_id,
            user_id,
            "assistant",
            response_text,
            {
                "reply_to": user_message["id"],
                "task_id": task_id,
                "used_context": used_context,
                "model": selected_model,
                "fallback_used": fallback_used,
                "warning": warning,
                "model_errors": model_errors[:5],
            },
        )
        return assistant_message, used_context

    def history(self, workspace_id: str) -> list[dict[str, Any]]:
        return self._recent_history(workspace_id, limit=40)

    def livekit_token(self, *, workspace_id: str, identity: str, display_name: str) -> tuple[str, str]:
        settings = get_settings()
        room = f"kobo-{workspace_id}"
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "iss": settings.livekit_api_key,
            "sub": identity,
            "name": display_name,
            "nbf": int((now - timedelta(seconds=10)).timestamp()),
            "exp": int((now + timedelta(hours=2)).timestamp()),
            "video": {
                "roomJoin": True,
                "room": room,
                "canPublish": True,
                "canSubscribe": True,
                "canPublishData": True,
            },
        }
        token = jwt.encode(payload, settings.livekit_api_secret, algorithm="HS256")
        return token, room


WORKSPACE_ASSISTANT = WorkspaceAssistantService()
