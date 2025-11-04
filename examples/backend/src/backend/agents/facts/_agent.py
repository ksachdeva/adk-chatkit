from typing import Final

from adk_chatkit import remove_client_tool_calls
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

from ._state import FactContext
from ._tools import get_weather, save_fact, switch_theme

_INSTRUCTIONS: Final[str] = (
    "You are ChatKit Guide, an onboarding assistant that primarily helps users "
    "understand how to use ChatKit and to record short factual statements "
    "about themselves. You may also provide weather updates when asked. You "
    "should never answer questions that are unrelated to ChatKit, the facts "
    "you are collecting, or weather requests. Instead, politely steer the user "
    "back to discussing ChatKit, sharing facts about themselves, or clarify the "
    "weather location they are interested in."
    "\n\n"
    "Begin every new thread by encouraging the user to tell you about "
    "themselves, starting with the question 'Tell me about yourself.' "
    "If they don't share facts proactively, ask questions to uncover concise facts such as "
    "their role, location, favourite tools, etc. Each time "
    "the user shares a concrete fact, call the `save_fact` tool with a "
    "short, declarative summary so it is recorded immediately."
    "\n\n"
    "The chat interface supports light and dark themes. When a user asks to switch "
    "themes, call the `switch_theme` tool with the `theme` parameter set to light or dark "
    "to match their request before replying. After switching, briefly confirm the change "
    "in your response."
    "\n\n"
    "When a user asks about the weather in a specific place, call the `get_weather` tool "
    "with their requested location and preferred units (Fahrenheit by default, Celsius if "
    "they ask). After the widget renders, summarize the key highlights in your reply."
    "\n\n"
    "When you refuse a request, explain briefly that you can only help with "
    "ChatKit guidance, collecting facts, or sharing weather updates."
)


def _ensure_context(callback_context: CallbackContext) -> None:
    context = callback_context.state.get("context", None)
    facts_context: FactContext | None
    if context is None:
        facts_context = None
    else:
        facts_context = FactContext.model_validate(context)

    if not facts_context:
        facts_context = FactContext()
        callback_context.state["context"] = facts_context.model_dump()


class FactsAgent(LlmAgent):
    def __init__(
        self,
        llm: LiteLlm,
        generate_content_config: genai_types.GenerateContentConfig | None = None,
    ) -> None:
        self._llm = llm

        super().__init__(
            name="facts_agent",
            description="ChatKit Guide and Facts Collector",
            model=self._llm,
            instruction=_INSTRUCTIONS,
            tools=[
                get_weather,
                save_fact,
                switch_theme,
            ],
            before_agent_callback=_ensure_context,
            before_model_callback=remove_client_tool_calls,
            generate_content_config=generate_content_config,
        )
