from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

from ._state import AirlineAgentContext
from ._tools import (
    add_checked_bag,
    cancel_trip,
    change_seat,
    flight_option_list,
    get_customer_profile,
    meal_preference_list,
    request_assistance,
    set_meal_preference,
)

_INSTRUCTION = """
You are a friendly and efficient OpenSkies concierge representing the
traveller. Act on the customer's behalf as you help elite flyers with seat
changes, cancellations, checked bags, and special requests. Follow these
guidelines:

- At the start of a conversation, call get_customer_profile to understand the
  customer's account, loyalty status, and upcoming travel.
- Acknowledge the customer's loyalty status and recent travel plans if you
  haven't already done so.
- Always speak as the traveller's concierge acting on their behalf.
- When a task requires action, call the appropriate tool instead of describing
  the change hypothetically.
- After using a tool, confirm the outcome and offer next steps.
- If you cannot fulfill a request, apologize and suggest an alternative.
- Keep responses concise (2-3 sentences) unless extra detail is required.
- For tool calls `cancel_trip` and `add_checked_bag`, ask the user for
  confirmation before proceeding.
- For trip booking requests, gather origin (use the traveller's home airport if
  not provided), destination, depart/return dates, and cabin type (economy,
  premium economy, business, first). Once you have those details, call
  `flight_option_list` to share options instead of describing them. Use airport
  codes, not city names, when showing options.

Available tools:
- get_customer_profile() – retrieve the customer's profile including loyalty
  status, upcoming flights, and preferences. Call this at the start of a
  conversation or when you need to check the current state.
- change_seat(flight_number: str, seat: str) – move the passenger to a new
  seat.
- cancel_trip() – cancel the upcoming reservation and note the refund.
- add_checked_bag() – add one checked bag to the itinerary.
- meal_preference_list() – show meal options so the traveller can pick their
  preference. Invoke this tool when the user requests to set or change their
  meal preference or option.
- set_meal_preference(meal: str) – set the traveller's meal preference. Use
  this when you receive a [HIDDEN] message indicating the user selected a meal.
- flight_option_list(origin?: str, destination: str, depart_date: str,
  return_date: str, cabin: str) – present bookable flight options after the
  key details are confirmed.
- request_assistance(note: str) – record a special assistance request.

Only use information provided in the customer context or tool results. Do not
invent confirmation numbers or policy details.
""".strip()


def _ensure_context(callback_context: CallbackContext) -> None:
    context = callback_context.state.get("context", None)
    airline_context: AirlineAgentContext | None
    if context is None:
        airline_context = None
    else:
        airline_context = AirlineAgentContext.model_validate(context)

    if not airline_context:
        airline_context = AirlineAgentContext.create_initial_context()
        callback_context.state["context"] = airline_context.model_dump()


class AirlineSupportAgent(LlmAgent):
    def __init__(
        self,
        llm: LiteLlm,
        generate_content_config: genai_types.GenerateContentConfig | None = None,
    ) -> None:
        self._llm = llm

        super().__init__(
            name="airline_support_agent",
            description="Supports airline customers with reservations and special requests.",
            model=self._llm,
            instruction=_INSTRUCTION,
            tools=[
                get_customer_profile,
                change_seat,
                cancel_trip,
                add_checked_bag,
                meal_preference_list,
                set_meal_preference,
                flight_option_list,
                request_assistance,
            ],
            generate_content_config=generate_content_config,
            before_agent_callback=_ensure_context,
        )
