"""This is a temporary agent to help develop the backend service."""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

_INSTRUCTION = """You are an agent that specializes in helping users with their queries."""


class TempAgent(LlmAgent):
    def __init__(
        self,
        llm: LiteLlm,
        generate_content_config: genai_types.GenerateContentConfig | None = None,
    ) -> None:
        self._llm = llm

        super().__init__(
            name="temp_agent",
            description="Only helps with philosophical questions.",
            model=self._llm,
            instruction=_INSTRUCTION,
            tools=[],
            generate_content_config=generate_content_config,
        )
