from __future__ import annotations

import logging
import random
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import uuid4

from adk_chatkit import (
    ADKAgentContext,
    ADKChatKitServer,
    ADKContext,
    ADKStore,
    ChatkitRunConfig,
    serialize_widget_item,
    stream_agent_response,
)
from adk_chatkit._constants import CHATKIT_WIDGET_STATE_KEY
from chatkit.actions import Action
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ClientEffectEvent,
    ClientToolCallItem,
    ThreadItemDoneEvent,
    ThreadItemUpdated,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
    WidgetItem,
    WidgetRootUpdated,
)
from google.adk.agents.run_config import StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types as genai_types
from pydantic import ValidationError

from backend._config import Settings
from backend._runner_manager import RunnerManager

from ._agent import AirlineSupportAgent
from ._state import AirlineAgentContext, FlightSegment
from ._title_agent import TitleAgent
from .widgets import (
    FLIGHT_SELECT_ACTION_TYPE,
    SET_MEAL_PREFERENCE_ACTION_TYPE,
    FlightOption,
    FlightSearchRequest,
    FlightSelectPayload,
    SetMealPreferencePayload,
    build_flight_options_widget,
    build_meal_preference_widget,
    describe_flight_option,
    generate_flight_options,
    meal_preference_label,
)

BOOKING_CONFIRM_ACTION_TYPE = "booking.confirm_selection"
BOOKING_MODIFY_ACTION_TYPE = "booking.modify_request"
UPSELL_ACCEPT_ACTION_TYPE = "upsell.accept"
UPSELL_DECLINE_ACTION_TYPE = "upsell.decline"
REBOOK_SELECT_ACTION_TYPE = "rebook.select_option"

logger = logging.getLogger(__name__)


def _make_airline_support_agent(settings: Settings) -> AirlineSupportAgent:
    return AirlineSupportAgent(
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


def _is_tool_completion_item(item: Any) -> bool:
    return isinstance(item, ClientToolCallItem)


class AirlineSupportChatKitServer(ADKChatKitServer):
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

        # Create agents and runners
        agent = _make_airline_support_agent(settings)
        title_agent = _make_title_agent(settings)

        self._runner = runner_manager.add_runner(settings.AIRLINE_APP_NAME, agent)
        self._title_runner = runner_manager.add_runner(f"{settings.AIRLINE_APP_NAME}_title", title_agent)

    async def _get_context_from_session(
        self,
        context: ADKContext,
        thread_id: str,
    ) -> AirlineAgentContext:
        """Get airline context from ADK session state."""
        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=thread_id,
        )
        if not session:
            return AirlineAgentContext.create_initial_context()

        ctx_dict = session.state.get("context", None)
        if ctx_dict is None:
            return AirlineAgentContext.create_initial_context()
        return AirlineAgentContext.model_validate(ctx_dict)

    async def _save_widget_to_session(
        self,
        widget_item: WidgetItem,
        context: ADKContext,
    ) -> None:
        """Save a widget item to the session state so it can be loaded later."""
        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=widget_item.thread_id,
        )
        if not session:
            return

        timestamp = datetime.now().timestamp()
        state_delta = {
            CHATKIT_WIDGET_STATE_KEY: {widget_item.id: serialize_widget_item(widget_item)},
        }
        from google.adk.events import Event, EventActions

        system_event = Event(
            invocation_id=uuid4().hex,
            author="system",
            actions=EventActions(state_delta=state_delta),
            timestamp=timestamp,
        )
        await self._session_service.append_event(session, system_event)

    async def _save_context_to_session(
        self,
        ctx: AirlineAgentContext,
        thread_id: str,
        context: ADKContext,
    ) -> None:
        """Save the airline context back to session state."""
        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=thread_id,
        )
        if not session:
            return

        timestamp = datetime.now().timestamp()
        state_delta = {"context": ctx.model_dump()}
        from google.adk.events import Event, EventActions

        system_event = Event(
            invocation_id=uuid4().hex,
            author="system",
            actions=EventActions(state_delta=state_delta),
            timestamp=timestamp,
        )
        await self._session_service.append_event(session, system_event)

    def _profile_effect(self, ctx: AirlineAgentContext) -> ClientEffectEvent:
        return ClientEffectEvent(
            name="customer_profile/update",
            data={"profile": ctx.customer_profile.to_dict()},
        )

    async def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle widget actions."""
        if action.type == SET_MEAL_PREFERENCE_ACTION_TYPE:
            async for event in self._handle_meal_preference_action(thread, action, sender, context):
                yield event
        elif action.type == FLIGHT_SELECT_ACTION_TYPE:
            async for event in self._handle_flight_select_action(thread, action, sender, context):
                yield event
        elif action.type == BOOKING_CONFIRM_ACTION_TYPE:
            async for event in self._handle_booking_confirm_action(thread, action, sender, context):
                yield event
        elif action.type == BOOKING_MODIFY_ACTION_TYPE:
            async for event in self._handle_booking_modify_action(thread, action, sender, context):
                yield event
        elif action.type == UPSELL_ACCEPT_ACTION_TYPE:
            async for event in self._handle_upgrade_accept_action(thread, action, sender, context):
                yield event
        elif action.type == UPSELL_DECLINE_ACTION_TYPE:
            async for event in self._handle_upgrade_decline_action(thread, action, sender, context):
                yield event
        elif action.type == REBOOK_SELECT_ACTION_TYPE:
            async for event in self._handle_rebook_action(thread, action, sender, context):
                yield event

    async def _handle_meal_preference_action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        payload = self._parse_meal_preference_payload(action)
        if payload is None:
            return

        meal_label = meal_preference_label(payload.meal)

        if sender is not None:
            widget = build_meal_preference_widget(selected=payload.meal)
            yield ThreadItemUpdated(
                item_id=sender.id,
                update=WidgetRootUpdated(widget=widget),
            )

        # Re-run agent with hidden message to update state
        hidden_message = f"[HIDDEN]\nUser selected meal preference: {meal_label}"
        async for event in self._run_agent_with_message(thread, hidden_message, context):
            yield event

    async def _handle_flight_select_action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        payload = self._parse_flight_select_payload(action)
        if payload is None:
            return

        # Check if widget was already used
        ctx = await self._get_context_from_session(context, thread.id)
        if sender is not None and ctx.is_widget_consumed(sender.id):
            return

        try:
            options = [FlightOption.model_validate(opt) for opt in payload.options]
        except ValidationError as exc:
            logger.warning("Invalid flight options in payload: %s", exc)
            options = []

        if not options:
            options = generate_flight_options(payload.request)

        selected = next((opt for opt in options if opt.id == payload.id), None)
        if selected is None:
            return

        # Lock the current widget to the chosen option
        if sender is not None:
            selected_widget = build_flight_options_widget(
                [selected],
                payload.request,
                selected_id=selected.id,
                leg=payload.leg,
            )
            yield ThreadItemUpdated(
                item_id=sender.id,
                update=WidgetRootUpdated(widget=selected_widget),
            )
            # Mark widget as consumed
            ctx.mark_widget_consumed(sender.id)

        # Record the flight booking in context
        seat_assignment = _pick_default_seat(payload.request.cabin)
        flight_number = _generate_flight_number(payload.leg)
        booking = ctx.record_flight_booking(
            flight_number=flight_number,
            date=payload.request.depart_date,
            origin=payload.request.normalized_origin(),
            destination=payload.request.normalized_destination(),
            depart_time=selected.dep_time,
            arrival_time=selected.arr_time,
            seat=seat_assignment,
        )

        # Save context back to session
        await self._save_context_to_session(ctx, thread.id, context)

        summary = describe_flight_option(selected, payload.request)
        action_text = (
            "You're scheduled on that option. I'll surface a few returns now."
            if payload.leg == "outbound"
            else "Return scheduled. Want me to watch for upgrades?"
        )
        yield ThreadItemDoneEvent(
            item=self._assistant_message(
                thread,
                f"Scheduled: {summary}. Seat {booking.seat} for now; {action_text}",
                context,
            ),
        )

        # Send profile update effect
        yield self._profile_effect(ctx)

        # Show return options for outbound leg
        if payload.leg == "outbound":
            return_request = FlightSearchRequest(
                origin=payload.request.normalized_destination(),
                destination=payload.request.normalized_origin(),
                depart_date=payload.request.return_date,
                return_date=payload.request.depart_date,
                cabin=payload.request.cabin,
            )
            return_options = generate_flight_options(return_request)
            yield ThreadItemDoneEvent(
                item=self._assistant_message(
                    thread,
                    "Here are return options that line up with your trip:",
                    context,
                ),
            )
            new_widget = build_flight_options_widget(
                return_options,
                return_request,
                leg="return",
            )
            return_widget_id = uuid4().hex
            return_widget_item = WidgetItem(
                thread_id=thread.id,
                id=return_widget_id,
                created_at=datetime.now(),
                widget=new_widget,
            )
            # Save widget to session so it can be loaded when user clicks on it
            await self._save_widget_to_session(return_widget_item, context)
            yield ThreadItemDoneEvent(item=return_widget_item)

    async def _handle_booking_confirm_action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        _sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        payload = action.payload or {}
        destination = payload.get("destination", "the trip")
        depart_label = payload.get("depart_label", "outbound flight")
        return_label = payload.get("return_label", "return flight")

        hidden_message = (
            f"[HIDDEN]\n"
            f"User confirmed booking:\n"
            f"Destination: {destination}\n"
            f"Outbound: {depart_label}\n"
            f"Return: {return_label}"
        )
        async for event in self._run_agent_with_message(thread, hidden_message, context):
            yield event

    async def _handle_booking_modify_action(
        self,
        thread: ThreadMetadata,
        _action: Action[str, Any],
        _sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        yield ThreadItemDoneEvent(
            item=self._assistant_message(
                thread,
                (
                    "Happy to tweak the plan. Let me know what you'd like to "
                    "change and feel free to attach a new inspiration photo "
                    "if it helps."
                ),
                context,
            ),
        )

    async def _handle_upgrade_accept_action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        _sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        async for event in self._handle_upgrade_action(thread, action, context, accepted=True):
            yield event

    async def _handle_upgrade_decline_action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        _sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        async for event in self._handle_upgrade_action(thread, action, context, accepted=False):
            yield event

    async def _handle_upgrade_action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        context: ADKContext,
        *,
        accepted: bool,
    ) -> AsyncIterator[ThreadStreamEvent]:
        cabin = (action.payload or {}).get("cabin_name", "the upgrade")
        price = (action.payload or {}).get("price", "the quoted amount")

        if accepted:
            hidden_message = f"[HIDDEN]\nUser accepted {cabin} upgrade for {price}."
        else:
            hidden_message = f"[HIDDEN]\nUser declined {cabin} upgrade."

        async for event in self._run_agent_with_message(thread, hidden_message, context):
            yield event

    async def _handle_rebook_action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        _sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        payload = action.payload or {}
        flight_number = payload.get("flight_number")
        option_id = payload.get("option_id")
        depart_time = payload.get("depart_time")
        arrival_time = payload.get("arrival_time")
        note = payload.get("option_note", "Selected alternate time")

        if not flight_number or option_id is None:
            return

        if option_id == "keep":
            yield ThreadItemDoneEvent(
                item=self._assistant_message(
                    thread,
                    "Sounds good — we'll keep the original departure on file.",
                    context,
                ),
            )
            return

        hidden_message = (
            f"[HIDDEN]\n"
            f"User requested rebooking:\n"
            f"Flight: {flight_number}\n"
            f"New departure: {depart_time}\n"
            f"New arrival: {arrival_time}\n"
            f"Note: {note}"
        )
        async for event in self._run_agent_with_message(thread, hidden_message, context):
            yield event

    async def _run_agent_with_message(
        self,
        thread: ThreadMetadata,
        message_text: str,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Run agent with a hidden message to update state."""
        agent_context = ADKAgentContext(
            app_name=context.app_name,
            user_id=context.user_id,
            thread=thread,
        )

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=message_text)],
        )

        event_stream = self._runner.run_async(
            user_id=context.user_id,
            session_id=thread.id,
            new_message=content,
            run_config=ChatkitRunConfig(streaming_mode=StreamingMode.SSE, context=agent_context),
        )

        async for event in stream_agent_response(agent_context, event_stream):
            yield event

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

        # Update thread title if needed
        if thread.title is None:
            await self._maybe_update_thread_title(thread, message_text, context)

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

    async def _maybe_update_thread_title(
        self,
        thread: ThreadMetadata,
        message_text: str,
        context: ADKContext,
    ) -> None:
        """Generate and update thread title."""
        try:
            if len(message_text) > 50:
                thread.title = message_text[:47] + "..."
            else:
                thread.title = message_text
            await self._store.save_thread(thread, context)
        except Exception:
            pass

    @staticmethod
    def _parse_meal_preference_payload(action: Action[str, Any]) -> SetMealPreferencePayload | None:
        try:
            return SetMealPreferencePayload.model_validate(action.payload or {})
        except ValidationError as exc:
            logger.warning("Invalid meal preference payload: %s", exc)
            return None

    @staticmethod
    def _parse_flight_select_payload(action: Action[str, Any]) -> FlightSelectPayload | None:
        try:
            return FlightSelectPayload.model_validate(action.payload or {})
        except ValidationError as exc:
            logger.warning("Invalid flight selection payload: %s", exc)
            return None

    def _assistant_message(
        self,
        thread: ThreadMetadata,
        text: str,
        context: ADKContext,
    ) -> AssistantMessageItem:
        return AssistantMessageItem(
            thread_id=thread.id,
            id=uuid4().hex,
            created_at=datetime.now(),
            content=[AssistantMessageContent(text=text)],
        )


def _generate_flight_number(leg: str) -> str:
    suffix = "1" if leg == "outbound" else "2"
    return f"OA9{suffix}7"


def _pick_default_seat(cabin: str) -> str:
    """Return a randomized seat assignment biased by fare class."""
    normalized = cabin.lower().strip()
    seat_letters = {
        "first": ["A", "D"],
        "business": ["A", "C", "D", "F"],
        "premium economy": list("ABCDEF"),
        "economy": list("ABCDEF"),
    }
    row_ranges = {
        "first": (1, 3),
        "business": (4, 9),
        "premium economy": (10, 19),
        "economy": (20, 45),
    }
    letters = seat_letters.get(normalized, list("ABCDEF"))
    start, end = row_ranges.get(normalized, (12, 38))
    row = random.randint(start, end)
    return f"{row}{random.choice(letters)}"
