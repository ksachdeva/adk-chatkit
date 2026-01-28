from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

from chatkit.types import (
    ClientEffectEvent,
    ClientToolCallItem,
    HiddenContextItem,
    ThreadItem,
    ThreadItemDoneEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    WidgetItem,
)
from chatkit.widgets import WidgetRoot
from google.adk.agents.run_config import RunConfig
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from ._client_tool_call import ClientToolCallState
from ._event_utils import QueueCompleteSentinel


class ThreadItemStore(Protocol):
    """Protocol for stores that can add thread items."""

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: ADKContext) -> None:
        """Add a thread item to the store."""
        ...


class ADKContext(BaseModel):
    app_name: str
    user_id: str


class ADKAgentContext(ADKContext):
    thread: ThreadMetadata
    client_tool_call: ClientToolCallItem | None = None
    _store: ThreadItemStore | None = None

    _events: asyncio.Queue[ThreadStreamEvent | QueueCompleteSentinel] = asyncio.Queue()

    def set_store(self, store: ThreadItemStore) -> None:
        """Set the store for this context. Used for adding hidden context items."""
        self._store = store

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


async def stream_event(event: ThreadStreamEvent, tool_context: ToolContext) -> None:
    """Stream an event to the chat interface.

    Args:
        event: The event to stream.
        tool_context: The tool context associated with the event.
    """
    chatkit_run_config = tool_context._invocation_context.run_config
    if not isinstance(chatkit_run_config, ChatkitRunConfig):
        raise ValueError("Make sure to set run_config for runner to ChatkitRunConfig")

    await chatkit_run_config.context.stream(event)


async def stream_widget(widget: WidgetRoot, tool_context: ToolContext) -> None:
    """Stream a widget to the chat interface.

    Args:
        widget: The widget to stream.
        tool_context: The tool context associated with the widget.
    """
    chatkit_run_config = tool_context._invocation_context.run_config
    if not isinstance(chatkit_run_config, ChatkitRunConfig):
        raise ValueError("Make sure to set run_config for runner to ChatkitRunConfig")

    await chatkit_run_config.context.stream_widget(widget, tool_context)


async def issue_client_tool_call(
    client_tool_call: ClientToolCallState,
    tool_context: ToolContext,
) -> None:
    """Issue a client tool call to the chat interface.

    Args:
        client_tool_call: The client tool call state to issue.
        tool_context: The tool context associated with the client tool call.
    """
    chatkit_run_config = tool_context._invocation_context.run_config
    if not isinstance(chatkit_run_config, ChatkitRunConfig):
        raise ValueError("Make sure to set run_config for runner to ChatkitRunConfig")

    await chatkit_run_config.context.issue_client_tool_call(client_tool_call, tool_context)


async def stream_client_effect(
    name: str,
    data: dict[str, object],
    tool_context: ToolContext,
) -> None:
    """Stream a client effect event to the chat interface.

    Client effects are used to trigger client-side actions like updating UI state,
    showing notifications, or playing animations.

    Args:
        name: The effect name (e.g., "update_cat_status", "cat_say")
        data: The effect payload data
        tool_context: The tool context from the current tool call
    """
    event = ClientEffectEvent(
        name=name,
        data=data,
    )
    await stream_event(event, tool_context)


async def add_hidden_context(
    content: str,
    tool_context: ToolContext,
) -> None:
    """Add a hidden context item to the thread.

    Hidden context items are not displayed in the UI but are included in the
    agent's input, allowing tools to provide context that influences future
    agent responses.

    Args:
        content: The hidden context content
        tool_context: The tool context from the current tool call
    """
    chatkit_run_config = tool_context._invocation_context.run_config
    if not isinstance(chatkit_run_config, ChatkitRunConfig):
        raise ValueError("Make sure to set run_config for runner to ChatkitRunConfig")

    context = chatkit_run_config.context
    thread = context.thread

    if context._store is None:
        raise ValueError("Store not set on ADKAgentContext. Call context.set_store(store) before running agent.")

    hidden_context_item = HiddenContextItem(
        id=str(uuid4()),
        thread_id=thread.id,
        created_at=datetime.now(),
        content=content,
    )

    await context._store.add_thread_item(thread.id, hidden_context_item, context)
