from collections.abc import AsyncIterator
from datetime import datetime

from adk_chatkit import ADKContext, ADKRequestProcessor
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageContentPartAdded,
    AssistantMessageContentPartDone,
    AssistantMessageContentPartTextDelta,
    AssistantMessageItem,
    ThreadItemAddedEvent,
    ThreadItemUpdated,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import BaseSessionService
from google.genai import types as genai_types

from backend._config import Settings
from backend._runner_manager import RunnerManager

from ._agent import AirlineSupportAgent


def _make_airline_support_agent(settings: Settings) -> AirlineSupportAgent:
    return AirlineSupportAgent(
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


class AirlineSupportProcessor(ADKRequestProcessor):
    def __init__(
        self,
        session_service: BaseSessionService,
        runner_manager: RunnerManager,
        settings: Settings,
    ) -> None:
        super().__init__(session_service)
        agent = _make_airline_support_agent(settings)
        self._runner = runner_manager.add_runner(settings.AIRLINE_APP_NAME, agent)

    async def respond(
        self,
        adk_context: ADKContext,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
    ) -> AsyncIterator[ThreadStreamEvent]:
        if item is None:
            return

        message_text = _user_message_text(item)
        if not message_text:
            return

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=message_text)],
        )

        content_index = 0
        async for event in self._runner.run_async(
            user_id=adk_context["user_id"],
            session_id=thread.id,
            new_message=content,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            print("############## START EVENT ##############")
            print(event)

            if event.content is None:
                # we need to throw item added event first
                yield ThreadItemAddedEvent(
                    item=AssistantMessageItem(
                        id="__fake_id__",
                        content=[],
                        thread_id=thread.id,
                        created_at=datetime.now(),
                    )
                )

                # is it first event/message/part?
                chatkit_event = ThreadItemUpdated(
                    item_id="__fake_id__",
                    update=AssistantMessageContentPartAdded(
                        content_index=content_index,
                        content=AssistantMessageContent(text=""),
                    ),
                )
                # content_index += 1
                yield chatkit_event

            if event.content and event.content.parts and event.content.parts[0].text:
                for p in event.content.parts:
                    if p.text:
                        if event.partial:
                            chatkit_event = ThreadItemUpdated(
                                item_id="__fake_id__",
                                update=AssistantMessageContentPartTextDelta(
                                    delta=p.text,
                                    content_index=content_index,
                                ),
                            )
                        else:
                            chatkit_event = ThreadItemUpdated(
                                item_id="__fake_id__",
                                update=AssistantMessageContentPartDone(
                                    content=AssistantMessageContent(text=p.text),
                                    content_index=content_index,
                                ),
                            )
                        # content_index += 1
                        yield chatkit_event

            print("############## END EVENT ##############")
