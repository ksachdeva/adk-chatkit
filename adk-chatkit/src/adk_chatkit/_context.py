import asyncio
from datetime import datetime

from chatkit.types import ThreadItemDoneEvent, ThreadMetadata, ThreadStreamEvent, WidgetItem
from chatkit.widgets import WidgetRoot
from google.adk.agents.run_config import RunConfig
from google.adk.tools import ToolContext
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

    async def stream_widget(self, widget: WidgetRoot, tool_context: ToolContext) -> None:
        if tool_context.function_call_id is None:
            raise ValueError("tool_context.function_call_id is None")
        await self.stream(
            ThreadItemDoneEvent(
                item=WidgetItem(
                    id=tool_context.function_call_id,
                    thread_id=self.thread.id,
                    created_at=datetime.now(),
                    widget=widget,
                )
            )
        )

    def _complete(self) -> None:
        self._events.put_nowait(QueueCompleteSentinel())


class ChatkitRunConfig(RunConfig):
    context: ADKAgentContext
