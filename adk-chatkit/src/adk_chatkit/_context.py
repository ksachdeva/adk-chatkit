import asyncio
from datetime import datetime

from chatkit.types import ClientToolCallItem, ThreadItemDoneEvent, ThreadMetadata, ThreadStreamEvent, WidgetItem
from chatkit.widgets import WidgetRoot
from google.adk.agents.run_config import RunConfig
from google.adk.tools import ToolContext
from pydantic import BaseModel

from ._client_tool_call import ClientToolCallState
from ._event_utils import QueueCompleteSentinel


class ADKContext(BaseModel):
    app_name: str
    user_id: str


class ADKAgentContext(ADKContext):
    thread: ThreadMetadata
    client_tool_call: ClientToolCallItem | None = None

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

    async def issue_client_tool_call(
        self,
        client_tool_call: ClientToolCallState,
        tool_context: ToolContext,
    ) -> None:
        if tool_context.function_call_id is None:
            raise ValueError("tool_context.function_call_id is None")

        self.client_tool_call = ClientToolCallItem(
            id=tool_context.function_call_id,
            thread_id=self.thread.id,
            name=client_tool_call.name,
            arguments=client_tool_call.arguments,
            status=client_tool_call.status,
            created_at=datetime.now(),
            call_id=client_tool_call.id,
        )

    def _complete(self) -> None:
        self._events.put_nowait(QueueCompleteSentinel())


class ChatkitRunConfig(RunConfig):
    context: ADKAgentContext
