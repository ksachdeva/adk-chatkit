import asyncio

from chatkit.types import ThreadMetadata, ThreadStreamEvent
from google.adk.runners import RunConfig
from pydantic import BaseModel

from ._event_utils import QueueCompleteSentinel


class ADKContext(BaseModel):
    app_name: str
    user_id: str


class ADKAgentContext(ADKContext):
    thread: ThreadMetadata

    _events: asyncio.Queue[ThreadStreamEvent | QueueCompleteSentinel] = asyncio.Queue()

    async def stream(self, event: ThreadStreamEvent) -> None:
        await self._events.put(event)

    def _complete(self) -> None:
        self._events.put_nowait(QueueCompleteSentinel())


class ChatkitRunConfig(RunConfig):
    context: ADKAgentContext
