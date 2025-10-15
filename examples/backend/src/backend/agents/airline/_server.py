from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from adk_chatkit import ADKContext, ADKStore
from chatkit.server import ChatKitServer
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageContentPartAdded,
    AssistantMessageContentPartDone,
    AssistantMessageContentPartTextDelta,
    AssistantMessageItem,
    ClientToolCallItem,
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
from ._state import AirlineAgentContext, CustomerProfile


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


def _is_tool_completion_item(item: Any) -> bool:
    return isinstance(item, ClientToolCallItem)


def _format_customer_context(profile: CustomerProfile) -> str:
    segments = []
    for segment in profile.segments:
        segments.append(
            f"- {segment.flight_number} {segment.origin}->{segment.destination}"
            f" on {segment.date} seat {segment.seat} ({segment.status})"
        )
    summary = "\n".join(segments)
    timeline = profile.timeline[:3]
    recent = "\n".join(f"  * {entry['entry']} ({entry['timestamp']})" for entry in timeline)
    return (
        "Customer Profile\n"
        f"Name: {profile.name} ({profile.loyalty_status})\n"
        f"Loyalty ID: {profile.loyalty_id}\n"
        f"Contact: {profile.email}, {profile.phone}\n"
        f"Checked Bags: {profile.bags_checked}\n"
        f"Meal Preference: {profile.meal_preference or 'Not set'}\n"
        f"Special Assistance: {profile.special_assistance or 'None'}\n"
        "Upcoming Segments:\n"
        f"{summary}\n"
        "Recent Service Timeline:\n"
        f"{recent or '  * No service actions recorded yet.'}"
    )


class AirlineSupportChatkitServer(ChatKitServer[ADKContext]):
    def __init__(
        self,
        session_service: BaseSessionService,
        runner_manager: RunnerManager,
        settings: Settings,
    ) -> None:
        store = ADKStore(session_service)
        super().__init__(store)
        self._store = store
        agent = _make_airline_support_agent(settings)
        self._session_service = session_service
        self._runner = runner_manager.add_runner(settings.AIRLINE_APP_NAME, agent)

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

        session = await self._session_service.get_session(
            app_name=context["app_name"],
            user_id=context["user_id"],
            session_id=thread.id,
        )

        assert session is not None

        airline_context_json = session.state.get("context", None)

        if airline_context_json:
            airline_context = AirlineAgentContext.model_validate(airline_context_json)
        else:
            airline_context = AirlineAgentContext.create_initial_context()
            session.state["context"] = airline_context.model_dump()

        context_prompt = _format_customer_context(airline_context.customer_profile)

        combined_prompt = f"{context_prompt}\n\nCurrent request: {message_text}\nRespond as the OpenSkies concierge."

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=combined_prompt)],
        )

        content_index = 0
        async for event in self._runner.run_async(
            user_id=context["user_id"],
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
