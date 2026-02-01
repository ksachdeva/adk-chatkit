"""
List widget for picking one of the metro lines.
"""

from __future__ import annotations

from typing import Any

from chatkit.widgets import ListView, WidgetRoot

from ..data.metro_map_store import Line


def build_line_select_widget(lines: list[Line], selected: str | None = None) -> WidgetRoot:
    """Render a line selector widget from the provided line metadata."""
    items: list[dict[str, Any]] = []
    for line in lines:
        is_selected = selected and selected == line.id
        text_color = "gray-900" if (not selected) or is_selected else "gray-300"

        children: list[dict[str, Any]] = [
            {
                "type": "Box",
                "size": 25,
                "radius": "full",
                "background": line.color,
            },
            {
                "type": "Text",
                "value": line.name,
                "color": text_color,
                "size": "sm",
            },
        ]

        if is_selected:
            children.append(
                {
                    "type": "Icon",
                    "name": "check",
                    "size": "xl",
                }
            )

        item_data: dict[str, Any] = {
            "type": "ListViewItem",
            "key": line.id,
            "gap": 5,
            "children": children,
        }

        if not selected:
            item_data["onClickAction"] = {
                "type": "line.select",
                "payload": {"id": line.id},
                "handler": "server",
            }

        items.append(item_data)

    widget_data = {"type": "ListView", "children": items}
    return ListView.model_validate(widget_data)
