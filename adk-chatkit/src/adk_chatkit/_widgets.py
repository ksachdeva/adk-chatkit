from typing import Any

from chatkit.widgets import WidgetRoot

from ._constants import WIDGET_KEY_IN_TOOL_RESPONSE


def add_widget_to_tool_response(
    response: dict[str, Any],
    widget: WidgetRoot,
) -> None:
    """Add a widget to a tool response dictionary.

    Args:
        response: The tool response dictionary to modify.
        widget: The widget to add.
    """
    response[WIDGET_KEY_IN_TOOL_RESPONSE] = widget
