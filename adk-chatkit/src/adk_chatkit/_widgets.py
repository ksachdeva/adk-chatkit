import json
from typing import Any

from chatkit.types import WidgetItem


def serialize_widget_item(widget: WidgetItem) -> dict[str, Any]:
    json_dump = widget.model_dump_json(exclude_none=True)
    return json.loads(json_dump)  # type: ignore
