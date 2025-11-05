import asyncio
from typing import cast

from adk_chatkit import ChatkitRunConfig, stream_event, stream_widget
from chatkit.types import ProgressUpdateEvent
from google.adk.tools import ToolContext

from ._tasks_widget import make_widget


async def render_tasks_widget(tool_context: ToolContext) -> dict[str, str]:
    """Renders a tasks widget."""

    result = dict(success="true")

    await stream_event(ProgressUpdateEvent(text="Fetching tasks widget..."), tool_context)
    await asyncio.sleep(2)

    widget = make_widget()

    await stream_widget(widget, tool_context)

    return result
