import asyncio
from datetime import datetime
from typing import cast

from adk_chatkit import ChatkitRunConfig
from chatkit.types import ProgressUpdateEvent, ThreadItemDoneEvent, WidgetItem
from google.adk.tools import ToolContext

from ._tasks_widget import make_widget


async def render_tasks_widget(tool_context: ToolContext) -> dict[str, str]:
    """Renders a tasks widget."""

    result = dict(success="true")

    # we are fetching the list of tasks
    run_config = tool_context._invocation_context.run_config
    assert run_config is not None

    chatkit_run_config = cast(ChatkitRunConfig, run_config)

    await chatkit_run_config.context.stream(ProgressUpdateEvent(text="Fetching tasks widget..."))
    await asyncio.sleep(2)
    await chatkit_run_config.context.stream(ProgressUpdateEvent(text=""))

    widget = make_widget()

    await chatkit_run_config.context.stream(
        ThreadItemDoneEvent(
            item=WidgetItem(
                id=tool_context.function_call_id,
                thread_id=chatkit_run_config.context.thread.id,
                created_at=datetime.now(),
                widget=widget,
            )
        )
    )

    return result
