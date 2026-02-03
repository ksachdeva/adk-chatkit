"""Flight options widget for the airline support agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from chatkit.widgets import ListView, WidgetRoot
from pydantic import BaseModel

FlightCabin = Literal["economy", "premium economy", "business", "first"]

FLIGHT_SELECT_ACTION_TYPE = "flight.select"
FlightLeg = Literal["outbound", "return"]


class FlightSearchRequest(BaseModel):
    """Minimal search context used to render flight options."""

    origin: str
    destination: str
    depart_date: str
    return_date: str
    cabin: str

    def normalized_origin(self) -> str:
        return _sanitize_airport_code(self.origin)

    def normalized_destination(self) -> str:
        return _sanitize_airport_code(self.destination)


class FlightOption(BaseModel):
    """Single flight option shown in the picker."""

    id: str
    from_airport: str
    to_airport: str
    dep_time: str
    arr_time: str
    date_label: str
    cabin: str

    model_config = {"populate_by_name": True}


class FlightSelectPayload(BaseModel):
    """Payload sent when the user taps a flight option."""

    id: str
    options: list[FlightOption]
    request: FlightSearchRequest
    leg: FlightLeg = "outbound"


def _sanitize_airport_code(raw: str) -> str:
    code = raw.strip().upper()
    if len(code) == 3 and code.isalpha():
        return code
    return code[:3]


def _format_date_label(raw_date: str) -> str:
    """Convert YYYY-MM-DD into a friendly label, otherwise return the input."""

    try:
        parsed = datetime.fromisoformat(raw_date)
        return f"{parsed.strftime('%a, %b ')}{parsed.day}"
    except Exception:
        return raw_date


def generate_flight_options(
    request: FlightSearchRequest,
) -> list[FlightOption]:
    """Return a small set of plausible flight options for the widget."""

    date_label = _format_date_label(request.depart_date)
    cabin_label = request.cabin.title()
    return [
        FlightOption(
            id="flight-morning",
            from_airport=request.normalized_origin(),
            to_airport=request.normalized_destination(),
            dep_time="08:10",
            arr_time="16:40",
            date_label=date_label,
            cabin=cabin_label,
        ),
        FlightOption(
            id="flight-midday",
            from_airport=request.normalized_origin(),
            to_airport=request.normalized_destination(),
            dep_time="12:35",
            arr_time="21:05",
            date_label=date_label,
            cabin=cabin_label,
        ),
        FlightOption(
            id="flight-late",
            from_airport=request.normalized_origin(),
            to_airport=request.normalized_destination(),
            dep_time="21:55",
            arr_time="06:20 (+1)",
            date_label=date_label,
            cabin=cabin_label,
        ),
    ]


def _serialize_option(option: FlightOption) -> dict[str, Any]:
    """Return a template-friendly dict for a flight option."""

    return {
        "id": option.id,
        "from_airport": option.from_airport,
        "to_airport": option.to_airport,
        "dep_time": option.dep_time,
        "arr_time": option.arr_time,
        "date_label": option.date_label,
        "cabin": option.cabin,
    }


def describe_flight_option(option: FlightOption, request: FlightSearchRequest) -> str:
    """Human-readable summary used in assistant replies and logs."""

    return (
        f"{option.cabin} {option.from_airport} → {option.to_airport} on "
        f"{_format_date_label(request.depart_date)} departing "
        f"{option.dep_time} (arrives {option.arr_time}); "
        f"return on {request.return_date}"
    )


def build_flight_options_widget(
    options: list[FlightOption],
    request: FlightSearchRequest,
    *,
    selected_id: str | None = None,
    leg: FlightLeg = "outbound",
) -> WidgetRoot:
    """Render the flight picker widget programmatically."""

    items: list[dict[str, Any]] = []
    for option in options:
        is_selected = selected_id == option.id

        item_data: dict[str, Any] = {
            "type": "ListViewItem",
            "key": option.id,
            "gap": 0,
            "align": "stretch",
            "children": [
                {
                    "type": "Box",
                    "width": "100%",
                    "padding": 3,
                    "border": {
                        "size": 1,
                        "color": "blue-500" if is_selected else "default",
                        "style": "solid" if is_selected else "dashed",
                    },
                    "radius": "xl",
                    "background": "surface",
                    "children": [
                        {
                            "type": "Row",
                            "gap": 3,
                            "align": "stretch",
                            "children": [
                                {
                                    "type": "Box",
                                    "width": 3,
                                    "background": "blue-600",
                                    "radius": "full",
                                },
                                {
                                    "type": "Col",
                                    "flex": "auto",
                                    "gap": 2,
                                    "children": [
                                        {
                                            "type": "Row",
                                            "children": [
                                                {
                                                    "type": "Title",
                                                    "value": f"{option.from_airport} → {option.to_airport}",
                                                    "size": "md",
                                                },
                                                {"type": "Spacer"},
                                                {
                                                    "type": "Badge",
                                                    "label": option.cabin,
                                                    "color": "discovery",
                                                    "variant": "soft",
                                                },
                                            ],
                                        },
                                        {
                                            "type": "Row",
                                            "children": [
                                                {
                                                    "type": "Col",
                                                    "children": [
                                                        {
                                                            "type": "Caption",
                                                            "value": "Depart",
                                                            "color": "secondary",
                                                        },
                                                        {
                                                            "type": "Title",
                                                            "value": option.dep_time,
                                                            "size": "lg",
                                                        },
                                                    ],
                                                },
                                                {"type": "Spacer"},
                                                {
                                                    "type": "Col",
                                                    "align": "end",
                                                    "children": [
                                                        {
                                                            "type": "Caption",
                                                            "value": "Arrive",
                                                            "color": "secondary",
                                                        },
                                                        {
                                                            "type": "Title",
                                                            "value": option.arr_time,
                                                            "size": "lg",
                                                        },
                                                    ],
                                                },
                                            ],
                                        },
                                        {"type": "Divider"},
                                        {
                                            "type": "Row",
                                            "children": [
                                                {
                                                    "type": "Caption",
                                                    "value": option.date_label,
                                                },
                                                {"type": "Spacer"},
                                                {
                                                    "type": "Caption",
                                                    "value": f"{option.from_airport} • {option.to_airport}",
                                                },
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }

        if not is_selected:
            item_data["onClickAction"] = {
                "type": FLIGHT_SELECT_ACTION_TYPE,
                "handler": "server",
                "payload": {
                    "id": option.id,
                    "options": [_serialize_option(opt) for opt in options],
                    "request": request.model_dump(mode="json"),
                    "leg": leg,
                },
            }

        items.append(item_data)

    widget_data = {"type": "ListView", "children": items}
    return ListView.model_validate(widget_data)
