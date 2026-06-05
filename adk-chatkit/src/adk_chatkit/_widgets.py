from typing import Any

from chatkit.types import WidgetItem


def serialize_widget_item(widget: WidgetItem) -> dict[str, Any]:
    return widget.model_dump(mode="json", exclude_none=True)
