from __future__ import annotations

from typing import Final

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

_INSTRUCTIONS: Final[str] = """
Generate a title for a conversation between an airline concierge acting on
behalf of the traveller and the user.
The first user message in the conversation is included below.
Do not just repeat the user message, use your own words.
YOU MUST respond with 2-5 words without punctuation.
"""


class TitleAgent(LlmAgent):
    def __init__(
        self,
        llm: LiteLlm,
        generate_content_config: genai_types.GenerateContentConfig | None = None,
    ) -> None:
        super().__init__(
            name="airline_title_generator",
            description="Generates short conversation titles for airline support chats.",
            model=llm,
            instruction=_INSTRUCTIONS,
            tools=[],
            generate_content_config=generate_content_config,
        )
