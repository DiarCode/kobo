from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.dependencies import require_workspace_member
from app.core.logging import configure_logging
from app.core.security import TokenError, decode_token
from app.core.store import STORE
from app.services.orchestration.event_bus import EVENT_BUS

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name, debug=settings.app_debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@dataclass
class PresenceState:
    connections: set[WebSocket] = field(default_factory=set)
    participants: dict[str, dict[str, object]] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


PRESENCE_ROOMS: dict[str, PresenceState] = {}


def _room(workspace_id: str) -> PresenceState:
    if workspace_id not in PRESENCE_ROOMS:
        PRESENCE_ROOMS[workspace_id] = PresenceState()
    return PRESENCE_ROOMS[workspace_id]


def _auth_websocket(websocket: WebSocket) -> dict[str, object] | None:
    token = websocket.cookies.get(settings.access_cookie_name)
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError:
        return None
    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        return None
    return STORE.users.get(user_id)


async def _send_presence_snapshot(websocket: WebSocket, workspace_id: str) -> None:
    room = _room(workspace_id)
    agents = STORE.workspace_agents.get(workspace_id, [])
    agent_participants = [
        {
            "id": str(agent["id"]),
            "kind": "agent",
            "name": str(agent["full_name"]),
            "status": str(agent["status"]),
            "x": float(agent.get("x", 30)),
            "y": float(agent.get("y", 45)),
            "avatar_key": str(agent.get("avatar_key", "char1")),
            "role_key": str(agent["role_key"]),
        }
        for agent in agents
    ]
    await websocket.send_text(
        json.dumps(
            {
                "type": "presence.snapshot",
                "participants": list(room.participants.values()) + agent_participants,
            }
        )
    )


async def _broadcast_presence(workspace_id: str, payload: dict[str, object]) -> None:
    room = _room(workspace_id)
    dead: list[WebSocket] = []
    message = json.dumps(payload)
    for connection in room.connections:
        try:
            await connection.send_text(message)
        except RuntimeError:
            dead.append(connection)
    for connection in dead:
        room.connections.discard(connection)


@app.websocket("/ws/workspaces/{workspace_id}/events")
async def workspace_events(websocket: WebSocket, workspace_id: str) -> None:
    user = _auth_websocket(websocket)
    if user is None:
        await websocket.close(code=1008)
        return
    try:
        require_workspace_member(workspace_id, str(user["id"]))
    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    queue = EVENT_BUS.subscribe(workspace_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(
                json.dumps(
                    {
                        "id": event.id,
                        "type": event.type,
                        "workspace_id": event.workspace_id,
                        "payload": event.payload,
                        "created_at": event.created_at.isoformat(),
                    }
                )
            )
    except WebSocketDisconnect:
        return


@app.websocket("/ws/workspaces/{workspace_id}/presence")
async def workspace_presence(websocket: WebSocket, workspace_id: str) -> None:
    user = _auth_websocket(websocket)
    if user is None:
        await websocket.close(code=1008)
        return
    try:
        require_workspace_member(workspace_id, str(user["id"]))
    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room = _room(workspace_id)
    profile = STORE.workspace_member_profiles.get(workspace_id, {}).get(str(user["id"]), {})
    participant_id = f"user:{user['id']}"
    participant = {
        "id": participant_id,
        "kind": "user",
        "name": str(profile.get("nickname", user["username"])),
        "status": "online",
        "x": float(profile.get("x", 15.0)),
        "y": float(profile.get("y", 70.0)),
        "avatar_key": str(profile.get("avatar_key", "char2")),
    }

    async with room.lock:
        room.connections.add(websocket)
        room.participants[participant_id] = participant

    await _send_presence_snapshot(websocket, workspace_id)
    await _broadcast_presence(workspace_id, {"type": "presence.joined", "participant": participant})
    EVENT_BUS.publish("workspace.presence.joined", workspace_id, {"participant_id": participant_id})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if not isinstance(data, dict):
                continue
            message_type = data.get("type")
            if message_type == "presence.move":
                x = float(data.get("x", participant["x"]))
                y = float(data.get("y", participant["y"]))
                participant["x"] = max(2.0, min(98.0, x))
                participant["y"] = max(2.0, min(95.0, y))
                status_value = data.get("status")
                if isinstance(status_value, str) and status_value in {"offline", "online", "working", "idle"}:
                    participant["status"] = status_value
                STORE.workspace_member_profiles.setdefault(workspace_id, {}).setdefault(str(user["id"]), {})
                STORE.workspace_member_profiles[workspace_id][str(user["id"])]["x"] = participant["x"]
                STORE.workspace_member_profiles[workspace_id][str(user["id"])]["y"] = participant["y"]
                room.participants[participant_id] = participant
                await _broadcast_presence(workspace_id, {"type": "presence.updated", "participant": participant})
            elif message_type == "presence.status":
                status_value = data.get("status")
                if isinstance(status_value, str) and status_value in {"offline", "online", "working", "idle"}:
                    participant["status"] = status_value
                    room.participants[participant_id] = participant
                    await _broadcast_presence(workspace_id, {"type": "presence.updated", "participant": participant})
    except WebSocketDisconnect:
        async with room.lock:
            room.connections.discard(websocket)
            room.participants.pop(participant_id, None)
        await _broadcast_presence(workspace_id, {"type": "presence.left", "participant_id": participant_id})
        EVENT_BUS.publish("workspace.presence.left", workspace_id, {"participant_id": participant_id})
