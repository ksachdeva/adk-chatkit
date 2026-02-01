from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, cast
from uuid import uuid4

from adk_chatkit import ADKAgentContext, ADKChatKitServer, ADKContext, ADKStore, ChatkitRunConfig, stream_agent_response
from chatkit.actions import Action
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ClientToolCallItem,
    ThreadItemDoneEvent,
    ThreadItemReplacedEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
    WidgetItem,
)
from google.adk.agents.run_config import StreamingMode
from google.adk.events import Event, EventActions
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types as genai_types

from backend._config import Settings
from backend._runner_manager import RunnerManager

from ._agent import CatAgent
from ._state import CatAgentContext as CatContext
from .widgets.name_suggestions_widget import CatNameSuggestion, build_name_suggestions_widget


def _make_cat_agent(settings: Settings) -> CatAgent:
    return CatAgent(
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


def _is_tool_completion_item(item: Any) -> bool:
    return isinstance(item, ClientToolCallItem)


class CatChatKitServer(ADKChatKitServer):
    def __init__(
        self,
        store: ADKStore,
        session_service: BaseSessionService,
        runner_manager: RunnerManager,
        settings: Settings,
    ) -> None:
        super().__init__(store)
        self._store = store
        agent = _make_cat_agent(settings)
        self._session_service = session_service
        self._runner = runner_manager.add_runner(settings.CAT_APP_NAME, agent)

    async def _run_agent_with_message(
        self,
        thread: ThreadMetadata,
        message: str,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Helper method to run the agent with a message string."""
        agent_context = ADKAgentContext(
            app_name=context.app_name,
            user_id=context.user_id,
            thread=thread,
        )

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=message)],
        )

        event_stream = self._runner.run_async(
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
        if action.type == "cats.select_name":
            async for event in self._handle_select_name_action(
                thread,
                action.payload,
                sender,
                context,
            ):
                yield event
            return

    async def _handle_select_name_action(
        self,
        thread: ThreadMetadata,
        payload: dict[str, Any],
        sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle the name selection action from the widget."""
        name = payload.get("name", "").strip()
        if not name or not sender:
            return

        # Get current state from the session service
        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=thread.id,
        )

        if not session:
            return

        cat_context_dict = session.state.get("context", None)
        if cat_context_dict is None:
            cat_context = CatContext.create_initial_context()
        else:
            cat_context = CatContext.model_validate(cat_context_dict)

        is_already_named = cat_context.name != "Unnamed Cat"
        selection = cat_context.name if is_already_named else name

        # Update the widget to show selection
        options_data = payload.get("options", [])
        options = [CatNameSuggestion(**opt) for opt in options_data]
        widget = build_name_suggestions_widget(options, selected=selection)

        yield ThreadItemReplacedEvent(
            item=sender.model_copy(update={"widget": widget}),
        )

        # Handle edge case: cat already named
        if is_already_named:
            message_item = AssistantMessageItem(
                id=uuid4().hex,
                thread_id=thread.id,
                created_at=datetime.now(),
                content=[
                    AssistantMessageContent(text=f"{cat_context.name} already has a name, so we can't rename them.")
                ],
            )
            yield ThreadItemDoneEvent(item=message_item)
            return

        # Update the thread title immediately
        cat_context.rename(name)
        title = f"{cat_context.name}'s Lounge"
        thread.title = title
        await self._store.save_thread(thread, context)

        # Create hidden message and run agent
        message_text = f"[HIDDEN]\nUser selected cat name: {name}"
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

        if _is_tool_completion_item(item):
            return

        message_text = _user_message_text(item)
        if not message_text:
            return

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=message_text)],
        )

        agent_context = ADKAgentContext(
            app_name=context.app_name,
            user_id=context.user_id,
            thread=thread,
        )

        event_stream = self._runner.run_async(
            user_id=context.user_id,
            session_id=thread.id,
            new_message=content,
            run_config=ChatkitRunConfig(streaming_mode=StreamingMode.SSE, context=agent_context),
        )

        async for event in stream_agent_response(agent_context, event_stream):
            yield event
