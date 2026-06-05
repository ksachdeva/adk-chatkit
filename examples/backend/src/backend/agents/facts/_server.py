from collections.abc import AsyncIterator
from typing import Any

from adk_chatkit import ADKAgentContext, ADKChatKitServer, ADKContext, ADKStore, ChatkitRunConfig, stream_agent_response
from chatkit.types import (
    ClientToolCallItem,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)
from google.adk.agents.run_config import StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

from backend._config import Settings
from backend._runner_manager import RunnerManager

from ._agent import FactsAgent


def _make_facts_agent(settings: Settings) -> FactsAgent:
    return FactsAgent(
        llm=LiteLlm(
            model=settings.gpt41_mini_agent.llm.model_name,
            **settings.gpt41_mini_agent.llm.provider_args,
        ),
        generate_content_config=settings.gpt41_mini_agent.generate_content,
    )


def _user_message_text(input_user_message: UserMessageItem) -> str:
    parts: list[str] = []
    for part in input_user_message.content:
        text = getattr(part, "text", None)
        if text:
            parts.append(text)
    return " ".join(parts).strip()


def _is_tool_completion_item(input_user_message: Any) -> bool:
    return isinstance(input_user_message, ClientToolCallItem)


class FactsChatKitServer(ADKChatKitServer):
    def __init__(
        self,
        store: ADKStore,
        runner_manager: RunnerManager,
        settings: Settings,
    ) -> None:
        super().__init__(store)
        agent = _make_facts_agent(settings)
        self._runner = runner_manager.add_runner(settings.FACTS_APP_NAME, agent)

    async def _adk_respond(
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
