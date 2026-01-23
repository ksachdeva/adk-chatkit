from __future__ import annotations

from typing import Final

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

_INSTRUCTIONS: Final[str] = """
    Generate a short conversation title for a metro planning assistant chatting with a user.
    The first user message in the thread is included below to provide context. Use your own
    words, respond with 2-5 words, and avoid punctuation.
"""


class TitleAgent(LlmAgent):
    def __init__(
        self,
        llm: LiteLlm,
        generate_content_config: genai_types.GenerateContentConfig | None = None,
    ) -> None:
        super().__init__(
            name="metro_title_generator",
            description="Generates short conversation titles for metro planning chats.",
            model=llm,
            instruction=_INSTRUCTIONS,
            tools=[],
            generate_content_config=generate_content_config,
        )
