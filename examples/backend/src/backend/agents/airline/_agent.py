from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

from ._state import AirlineAgentContext
from ._tools import (
    add_checked_bag,
    cancel_trip,
    change_seat,
    get_customer_profile,
    request_assistance,
    set_meal_preference,
)

_INSTRUCTION = """
You are a friendly and efficient airline customer support agent for OpenSkies.
You help elite flyers with seat changes, cancellations, checked bags, and
special requests. Follow these guidelines:

- Always acknowledge the customer's loyalty status and recent travel plans.
- When a task requires action, call the appropriate tool instead of describing
  the change hypothetically.
- After using a tool, confirm the outcome and offer next steps.
- If you cannot fulfill a request, apologise and suggest an alternative.
- Keep responses concise (2-3 sentences) unless extra detail is required.

Available tools:
- get_customer_profile() - retrieve the customer's profile and recent activity.
- change_seat(flight_number: str, seat: str) - move the passenger to a new seat.
- cancel_trip() - cancel the upcoming reservation and note the refund.
- add_checked_bag() - add one checked bag to the itinerary.
- set_meal_preference(meal: str) - update meal preference (e.g. vegetarian).
- request_assistance(note: str) - record a special assistance request.

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
                set_meal_preference,
                request_assistance,
            ],
            generate_content_config=generate_content_config,
            before_agent_callback=_ensure_context,
        )
