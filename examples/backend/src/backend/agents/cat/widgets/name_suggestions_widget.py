from __future__ import annotations

from typing import Any

from chatkit.widgets import ListView, WidgetRoot
from pydantic import BaseModel


class CatNameSuggestion(BaseModel):
    """Name idea paired with a short blurb describing the cat it fits."""

    name: str
    reason: str | None = None


def build_name_suggestions_widget(
    names: list[CatNameSuggestion],
    selected: str | None = None,
) -> WidgetRoot:
    """Render the selectable list widget for cat name suggestions."""
    print(f"Building name suggestions widget with selected: {selected}")
    print(f"Names: {names}")

    # Build widget JSON structure programmatically
    items = []
    for suggestion in names:
        is_selected = selected and selected == suggestion.name
        icon_color = "gray-200" if selected and not is_selected else "gray-300"
        if is_selected:
            icon_color = "success"

        item_data: dict[str, Any] = {
            "type": "ListViewItem",
            "key": suggestion.name,
            "children": [
                {
                    "type": "Row",
                    "gap": 3,
                    "align": "center",
                    "children": [
                        {
                            "type": "Icon",
                            "name": "check" if is_selected else "dot",
                            "color": icon_color,
                            "size": "xl",
                        },
                        {
                            "type": "Col",
                            "gap": 1,
                            "children": [
                                {
                                    "type": "Text",
                                    "value": suggestion.name,
                                    "weight": "semibold",
                                    **(
                                        {"color": "emphasis"}
                                        if is_selected
                                        else ({"color": "tertiary"} if selected else {})
                                    ),
                                },
                                *(
                                    [
                                        {
                                            "type": "Text",
                                            "value": suggestion.reason or "",
                                            "color": "tertiary",
                                            "size": "sm",
                                        }
                                    ]
                                    if suggestion.reason
                                    else []
                                ),
                            ],
                        },
                    ],
                }
            ],
        }

        if not selected:
            item_data["onClickAction"] = {
                "type": "cats.select_name",
                "handler": "client",
                "payload": {
                    "name": suggestion.name,
                    "options": [s.model_dump() for s in names],
                },
            }

        items.append(item_data)

    # Add "more names" button
    items.append(
        {
            "type": "ListViewItem",
            "key": "more",
            "children": [
                {
                    "type": "Button",
                    "onClickAction": {
                        "type": "cats.more_names",
                        "handler": "client",
                        "payload": {},
                    },
                    "variant": "outline",
                    "color": "discovery",
                    "size": "lg",
                    "pill": True,
                    "block": True,
                    "label": "Suggest more names",
                    "iconEnd": "sparkle",
                    "disabled": selected is not None,
                }
            ],
        }
    )

    widget_data = {"type": "ListView", "children": items}
    return ListView.model_validate(widget_data)
