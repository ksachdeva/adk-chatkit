"""
Widget helpers for presenting a list of events with timeline styling.
"""

from __future__ import annotations

from datetime import date, datetime
from itertools import groupby
from typing import Any, Iterable, Mapping

from chatkit.widgets import ListView, WidgetRoot

from ..data.event_store import EventRecord

CATEGORY_COLORS: dict[str, str] = {
    "community": "purple-400",
    "civics": "blue-400",
    "arts": "pink-400",
    "outdoors": "green-400",
    "music": "orange-400",
    "family": "yellow-400",
    "food": "red-400",
    "fitness": "teal-400",
}
DEFAULT_CATEGORY_COLOR = "gray-400"

EventLike = EventRecord | Mapping[str, Any]


def build_event_list_widget(
    events: Iterable[EventLike],
    selected_event_id: str | None = None,
) -> WidgetRoot:
    """Render an event list widget grouped by date programmatically."""
    records = [_coerce_event(event) for event in events]
    records.sort(key=lambda rec: rec.date)
    event_ids: list[str] = [record.id for record in records]

    items: list[dict[str, Any]] = []

    # Group events by date
    for event_date, group in groupby(records, key=lambda rec: rec.date):
        group_records = list(group)

        # Add date header
        items.append(
            {
                "type": "ListViewItem",
                "key": f"date-{event_date.isoformat()}",
                "children": [
                    {
                        "type": "Box",
                        "padding": {"top": 3, "bottom": 1},
                        "children": [
                            {
                                "type": "Caption",
                                "value": _format_date(event_date),
                                "weight": "semibold",
                            }
                        ],
                    }
                ],
            }
        )

        # Add events for this date
        for record in group_records:
            is_selected = selected_event_id and selected_event_id == record.id
            category = (record.category or "").strip().lower()
            color = CATEGORY_COLORS.get(category, DEFAULT_CATEGORY_COLOR)

            item_data: dict[str, Any] = {
                "type": "ListViewItem",
                "key": record.id,
                "children": [
                    {
                        "type": "Row",
                        "gap": 3,
                        "align": "start",
                        "children": [
                            {
                                "type": "Box",
                                "width": 4,
                                "flex": "none",
                                "align": "center",
                                "children": [
                                    {
                                        "type": "Box",
                                        "width": 3,
                                        "height": 3,
                                        "radius": "full",
                                        "background": color,
                                    }
                                ],
                            },
                            {
                                "type": "Col",
                                "gap": 1,
                                "flex": "auto",
                                "children": [
                                    {
                                        "type": "Text",
                                        "value": record.title,
                                        "weight": "semibold" if is_selected else "medium",
                                        "color": "emphasis" if is_selected else None,
                                    },
                                    {
                                        "type": "Row",
                                        "gap": 2,
                                        "children": [
                                            {
                                                "type": "Caption",
                                                "value": _format_time(record),
                                            },
                                            {
                                                "type": "Caption",
                                                "value": "·",
                                            },
                                            {
                                                "type": "Caption",
                                                "value": record.location,
                                            },
                                        ],
                                    },
                                    *(
                                        [
                                            {
                                                "type": "Text",
                                                "value": record.details,
                                                "size": "sm",
                                                "color": "secondary",
                                                "maxLines": 2,
                                            }
                                        ]
                                        if is_selected
                                        else []
                                    ),
                                ],
                            },
                        ],
                    }
                ],
            }

            # Add click action only if not selected
            if not selected_event_id:
                item_data["onClickAction"] = {
                    "type": "view_event_details",
                    "handler": "client",
                    "payload": {
                        "id": record.id,
                        "eventIds": event_ids,
                    },
                }

            items.append(item_data)

    widget_data = {"type": "ListView", "children": items}
    return ListView.model_validate(widget_data)


def _coerce_event(event: EventLike) -> EventRecord:
    if isinstance(event, EventRecord):
        return event
    return EventRecord.model_validate(event)


def _format_date(event_date: date) -> str:
    month = event_date.strftime("%b")
    weekday = event_date.strftime("%A")
    return f"{weekday}, {month} {event_date.day}"


def _format_time(record: EventRecord) -> str:
    value = datetime.combine(record.date, record.time)
    formatted = value.strftime("%I:%M %p")
    return formatted.lstrip("0")
