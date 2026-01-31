from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types


class TitleAgent(LlmAgent):
    def __init__(
        self,
        llm: LiteLlm,
        generate_content_config: genai_types.GenerateContentConfig | None = None,
    ) -> None:
        self._llm = llm

        super().__init__(
            name="title_generator",
            description="Generate a short conversation title for a news editorial assistant.",
            model=self._llm,
            instruction="""
    Generate a short conversation title for a news editorial assistant
    chatting with a user. The first user message in the thread is
    included below to provide context. Use your own words, respond with
    2-5 words, and avoid punctuation.
    """,
            tools=[],
            generate_content_config=generate_content_config,
        )
