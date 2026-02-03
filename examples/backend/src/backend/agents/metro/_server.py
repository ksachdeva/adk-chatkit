from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from adk_chatkit import ADKChatKitServer, ADKContext, ADKStore, ChatkitRunConfig, stream_agent_response
from chatkit.actions import Action
from chatkit.types import (
    ClientEffectEvent,
    ThreadItemReplacedEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
    WidgetItem,
)
from google.adk.agents.run_config import StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types as genai_types

from backend._config import Settings
from backend._runner_manager import RunnerManager

from ._agent import MetroMapAgent
from ._context import MetroMapAgentContext
from ._title_agent import TitleAgent
from .data.metro_map_store import MetroMapStore
from .widgets.line_select_widget import build_line_select_widget


def _make_metro_map_agent(settings: Settings) -> MetroMapAgent:
    return MetroMapAgent(
        llm=LiteLlm(
            model=settings.gpt41_mini_agent.llm.model_name,
            **settings.gpt41_mini_agent.llm.provider_args,
        ),
        generate_content_config=settings.gpt41_mini_agent.generate_content,
    )


def _make_title_agent(settings: Settings) -> TitleAgent:
    return TitleAgent(
        llm=LiteLlm(
            model=settings.gpt41_mini_agent.llm.model_name,
            **settings.gpt41_mini_agent.llm.provider_args,
        ),
        generate_content_config=settings.gpt41_mini_agent.generate_content,
    )


def _user_message_text(item: UserMessageItem) -> str:
    parts: list[str] = []
    for part in item.content:
        text = getattr(part, "text", None)
        if text:
            parts.append(text)
    return " ".join(parts).strip()


class MetroMapChatKitServer(ADKChatKitServer):
    """ChatKit server wired up with the metro map assistant."""

    def __init__(
        self,
        store: ADKStore,
        session_service: BaseSessionService,
        runner_manager: RunnerManager,
        settings: Settings,
    ) -> None:
        super().__init__(store)
        self._store = store
        self._session_service = session_service
        self._settings = settings

        # Initialize metro map store
        data_dir = Path(__file__).parent / "data"
        self.metro_map_store = MetroMapStore(data_dir)

        # Create agents and runners
        metro_agent = _make_metro_map_agent(settings)
        title_agent = _make_title_agent(settings)

        base_app_name = settings.METRO_MAP_APP_NAME
        self._metro_runner = runner_manager.add_runner(base_app_name, metro_agent)
        self._metro_runner_app_name = base_app_name

        self._title_runner = runner_manager.add_runner(f"{base_app_name}_title", title_agent)
        self._title_runner_app_name = f"{base_app_name}_title"

    async def _run_agent_with_message(
        self,
        thread: ThreadMetadata,
        message: str,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Helper method to run the agent with a message string."""
        agent_context = MetroMapAgentContext(
            app_name=self._metro_runner_app_name,
            user_id=context.user_id,
            thread=thread,
            metro_map_store=self.metro_map_store,
        )

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=message)],
        )

        event_stream = self._metro_runner.run_async(
            user_id=context.user_id,
            session_id=thread.id,
            new_message=content,
            run_config=ChatkitRunConfig(streaming_mode=StreamingMode.SSE, context=agent_context),
        )

        async for event in stream_agent_response(agent_context, event_stream):
            yield event

    async def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle widget actions."""
        if action.type == "line.select":
            if action.payload is None:
                return
            async for event in self._handle_line_select_action(thread, action.payload, sender, context):
                yield event
            return

    async def _handle_line_select_action(
        self,
        thread: ThreadMetadata,
        payload: dict[str, Any],
        sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle line selection from the widget."""
        line_id = payload["id"]

        # Update the widget to show the selected line and disable further clicks
        updated_widget = build_line_select_widget(
            self.metro_map_store.list_lines(),
            selected=line_id,
        )

        if sender:
            updated_widget_item = sender.model_copy(update={"widget": updated_widget})
            yield ThreadItemReplacedEvent(item=updated_widget_item)

        yield ClientEffectEvent(
            name="location_select_mode",
            data={"lineId": line_id},
        )

        # Create hidden message and run agent with expected tag format
        message_text = f"[HIDDEN]\n<LINE_SELECTED>{line_id}</LINE_SELECTED>"
        async for event in self._run_agent_with_message(thread, message_text, context):
            yield event

    async def _adk_respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        if item is None:
            return

        message_text = _user_message_text(item)
        if not message_text:
            return

        # Update thread title if needed
        if thread.title is None:
            await self._maybe_update_thread_title(thread, message_text, context)

        # Create agent context with metro map store for tools
        agent_context = MetroMapAgentContext(
            app_name=self._metro_runner_app_name,
            user_id=context.user_id,
            thread=thread,
            metro_map_store=self.metro_map_store,
        )

        # Run the agent (ADK session handles conversation history automatically)
        event_stream = self._metro_runner.run_async(
            user_id=context.user_id,
            session_id=thread.id,
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=message_text)],
            ),
            run_config=ChatkitRunConfig(streaming_mode=StreamingMode.SSE, context=agent_context),
        )

        async for event in stream_agent_response(agent_context, event_stream):
            yield event

    async def _maybe_update_thread_title(
        self,
        thread: ThreadMetadata,
        message_text: str,
        context: ADKContext,
    ) -> None:
        """Generate and update thread title using the title agent."""
        try:
            if len(message_text) > 50:
                thread.title = message_text[:47] + "..."
            else:
                thread.title = message_text
            await self._store.save_thread(thread, context)
        except Exception:
            # Don't fail the request if title generation fails
            pass
