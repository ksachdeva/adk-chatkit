from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, cast
from uuid import uuid4

from adk_chatkit import ADKAgentContext, ADKContext, ADKStore, ChatkitRunConfig, stream_agent_response
from chatkit.actions import Action
from chatkit.server import ChatKitServer
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
from ._state import CatState
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


class CatChatkitServer(ChatKitServer[ADKContext]):
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

        current_state = CatState.from_dict(cat_context.cat_state)
        is_already_named = current_state.name != "Unnamed Cat"
        selection = current_state.name if is_already_named else name

        options_data = payload.get("options", [])
        options = [CatNameSuggestion(**opt) for opt in options_data]
        widget = build_name_suggestions_widget(options, selected=selection)

        yield ThreadItemReplacedEvent(
            item=sender.model_copy(update={"widget": widget}),
        )

        if is_already_named:
            message_item = AssistantMessageItem(
                id=self._store.generate_item_id("message", thread, context),
                thread_id=thread.id,
                created_at=datetime.now(),
                content=[
                    AssistantMessageContent(text=f"{current_state.name} already has a name, so we can't rename them.")
                ],
            )
            yield ThreadItemDoneEvent(item=message_item)
            return

        # Save the name in the cat store and update the thread title
        state = CatState.from_dict(cat_context.cat_state)
        state.rename(name)
        cat_context.cat_state = state.to_dict()

        # Update session state via append_event (works for in-memory + db services)
        state_delta: dict[str, object] = {"context": cast(object, cat_context.model_dump())}
        system_event = Event(
            invocation_id=uuid4().hex,
            author="system",
            actions=EventActions(state_delta=state_delta),
            timestamp=datetime.now().timestamp(),
        )
        await self._session_service.append_event(session, system_event)

        title = f"{state.name}'s Lounge"
        thread.title = title
        await self._store.save_thread(thread, context)

        message_item = AssistantMessageItem(
            id=self._store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[
                AssistantMessageContent(
                    text=f"Love that choice. {state.name}'s profile card is now ready. Would you like to check it out?"
                )
            ],
        )
        yield ThreadItemDoneEvent(item=message_item)

    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        if input_user_message is None:
            return

        if _is_tool_completion_item(input_user_message):
            return

        message_text = _user_message_text(input_user_message)
        if not message_text:
            return

        # Inject persisted cat state into the prompt so the agent knows the name/stats
        try:
            session = await self._session_service.get_session(
                app_name=context.app_name,
                user_id=context.user_id,
                session_id=thread.id,
            )
            if session:
                ctx = session.state.get("context")
                if ctx:
                    cat_ctx = CatContext.model_validate(ctx)
                    cat_state = CatState.from_dict(cat_ctx.cat_state)
                    summary = (
                        f"[CAT_STATE] name={cat_state.name}; "
                        f"color={cat_state.color_pattern}; "
                        f"energy={cat_state.energy}; "
                        f"happiness={cat_state.happiness}; "
                        f"cleanliness={cat_state.cleanliness}; "
                        f"age={cat_state.age} [/CAT_STATE]"
                    )
                    message_text = f"{summary}\n\n{message_text}"
        except Exception:
            pass

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
