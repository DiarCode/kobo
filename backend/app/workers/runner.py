from __future__ import annotations

import asyncio
import logging

from app.services.orchestration.event_bus import EVENT_BUS

logger = logging.getLogger(__name__)


async def outbox_logger() -> None:
    index = 0
    while True:
        await asyncio.sleep(2)
        outbox = EVENT_BUS.outbox
        if len(outbox) > index:
            for event in outbox[index:]:
                logger.info("processed event id=%s type=%s workspace=%s", event.id, event.type, event.workspace_id)
            index = len(outbox)


if __name__ == "__main__":
    asyncio.run(outbox_logger())
