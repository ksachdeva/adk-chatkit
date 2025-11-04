from collections.abc import AsyncIterator
from typing import Any

from adk_chatkit import ADKAgentContext, ADKContext, ADKStore, ChatkitRunConfig, stream_agent_response
from chatkit.actions import Action
from chatkit.server import ChatKitServer
from chatkit.types import (
    ClientToolCallItem,
    ThreadItemRemovedEvent,
    ThreadItemReplacedEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
    WidgetItem,
)
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types as genai_types

from backend._config import Settings
from backend._runner_manager import RunnerManager

from ._agent import WidgetsAgent
from ._tasks_widget import make_tasks_list_widget, make_widget


def _make_widgets_agent(settings: Settings) -> WidgetsAgent:
    return WidgetsAgent(
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


class WidgetsChatkitServer(ChatKitServer[ADKContext]):
    def __init__(
        self,
        store: ADKStore,
        session_service: BaseSessionService,
        runner_manager: RunnerManager,
        settings: Settings,
    ) -> None:
        super().__init__(store)
        agent = _make_widgets_agent(settings)
        self._session_service = session_service
        self._runner = runner_manager.add_runner(settings.WIDGETS_APP_NAME, agent)

    async def respond(
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

        enhanced_context = ADKAgentContext(
            app_name=context.app_name,
            user_id=context.user_id,
            thread=thread,
        )

        event_stream = self._runner.run_async(
            user_id=context.user_id,
            session_id=thread.id,
            new_message=content,
            run_config=ChatkitRunConfig(streaming_mode=StreamingMode.SSE, context=enhanced_context),
        )

        async for event in stream_agent_response(enhanced_context, event_stream):
            yield event

    async def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        if action.type == "tasks.view":
            assert sender is not None
            widget = make_tasks_list_widget()

            yield ThreadItemReplacedEvent(
                item=WidgetItem(
                    id=sender.id,
                    thread_id=thread.id,
                    widget=widget,
                    created_at=sender.created_at,
                )
            )

        if action.type == "nav.back":
            assert sender is not None
            widget = make_widget()
            yield ThreadItemReplacedEvent(
                item=WidgetItem(
                    id=sender.id,
                    thread_id=thread.id,
                    widget=widget,
                    created_at=sender.created_at,
                )
            )

        if action.type == "item.select":
            assert sender is not None
            yield ThreadItemReplacedEvent(
                item=sender,
            )
