from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Event:
    id: str
    type: str
    workspace_id: str
    payload: dict[str, Any]
    created_at: datetime


class InMemoryEventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[Event]]] = defaultdict(list)
        self._outbox: list[Event] = []

    def publish(self, event_type: str, workspace_id: str, payload: dict[str, Any]) -> Event:
        event = Event(
            id=str(uuid4()),
            type=event_type,
            workspace_id=workspace_id,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        self._outbox.append(event)
        for queue in self._queues[workspace_id]:
            queue.put_nowait(event)
        return event

    def subscribe(self, workspace_id: str) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._queues[workspace_id].append(queue)
        return queue

    @property
    def outbox(self) -> list[Event]:
        return self._outbox


EVENT_BUS = InMemoryEventBus()
