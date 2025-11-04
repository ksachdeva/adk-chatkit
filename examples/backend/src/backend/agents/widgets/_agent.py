from typing import Final

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

from ._tools import render_tasks_widget

_INSTRUCTIONS: Final[str] = """
You are a widgets agent that helps render widgets in chat. You have access to tools that can render widgets.

Depending on the user's request, you may choose to use one of the available tools to render a widget.

"""


class WidgetsAgent(LlmAgent):
    def __init__(
        self,
        llm: LiteLlm,
        generate_content_config: genai_types.GenerateContentConfig | None = None,
    ) -> None:
        self._llm = llm

        super().__init__(
            name="widget_agent",
            description="An agent that helps showing widgets in chat",
            model=self._llm,
            instruction=_INSTRUCTIONS,
            tools=[
                render_tasks_widget,
            ],
            generate_content_config=generate_content_config,
        )
