"""Meal preference widget for the airline support agent."""

from __future__ import annotations

from typing import Any, Literal

from chatkit.widgets import ListView, WidgetRoot
from pydantic import BaseModel

MealPreferenceOption = Literal[
    "vegetarian",
    "kosher",
    "gluten intolerant",
    "child",
]

SET_MEAL_PREFERENCE_ACTION_TYPE = "support.set_meal_preference"


class SetMealPreferencePayload(BaseModel):
    meal: MealPreferenceOption


_MEAL_PREFERENCE_LABELS: dict[MealPreferenceOption, str] = {
    "vegetarian": "Vegetarian",
    "kosher": "Kosher",
    "gluten intolerant": "Gluten intolerant",
    "child": "Child",
}

MEAL_PREFERENCE_ORDER: tuple[MealPreferenceOption, ...] = (
    "vegetarian",
    "kosher",
    "gluten intolerant",
    "child",
)


def meal_preference_label(value: MealPreferenceOption) -> str:
    return _MEAL_PREFERENCE_LABELS.get(value, value.title())


def build_meal_preference_widget(
    *,
    selected: MealPreferenceOption | None = None,
) -> WidgetRoot:
    """Render the meal preference list widget with optional selection state."""

    items: list[dict[str, Any]] = []
    for option_value in MEAL_PREFERENCE_ORDER:
        is_selected = selected == option_value
        label = meal_preference_label(option_value)

        item_data: dict[str, Any] = {
            "type": "ListViewItem",
            "key": option_value,
            "children": [
                {
                    "type": "Row",
                    "gap": 2,
                    "children": [
                        {
                            "type": "Icon",
                            "name": "check" if is_selected else "empty-circle",
                            "color": "secondary",
                        },
                        {
                            "type": "Text",
                            "value": label,
                            "weight": "semibold" if is_selected else "medium",
                            **({"color": "emphasis"} if is_selected else {}),
                        },
                    ],
                },
            ],
        }

        if not selected:
            item_data["onClickAction"] = {
                "type": SET_MEAL_PREFERENCE_ACTION_TYPE,
                "handler": "server",
                "payload": {"meal": option_value},
            }

        items.append(item_data)

    widget_data = {"type": "ListView", "children": items}
    return ListView.model_validate(widget_data)
