from __future__ import annotations

from chatkit.widgets import Card, WidgetRoot

from .._state import CatState


def _format_age_label(age: int) -> str:
    return "1 year" if age == 1 else f"{age} years"


def _format_color_pattern_label(color_pattern: str | None) -> str:
    if color_pattern is None:
        return "N/A"
    return color_pattern.capitalize()


def _format_favorite_toy(favorite_toy: str | None) -> str:
    if favorite_toy is None:
        return "A laser pointer"
    return favorite_toy.capitalize()


def _image_src(state: CatState) -> str:
    pattern = (state.color_pattern or "").strip().lower()
    if pattern == "black":
        return "https://files.catbox.moe/pbkakb.png"
    if pattern == "calico":
        return "https://files.catbox.moe/p2mj4g.png"
    if pattern == "colorpoint":
        return "https://files.catbox.moe/nrtexw.png"
    if pattern == "tabby":
        return "https://files.catbox.moe/zn77bd.png"
    if pattern == "white":
        return "https://files.catbox.moe/zvkhpo.png"
    # Fallback if no color pattern has been set yet
    return "https://files.catbox.moe/e42tgh.png"


def build_profile_card_widget(state: CatState, favorite_toy: str | None = None) -> WidgetRoot:
    """Build the cat profile card widget."""
    widget_data = {
        "type": "Card",
        "size": "sm",
        "padding": 0,
        "children": [
            {
                "type": "Box",
                "padding": {"x": 4, "y": 2},
                "background": {"light": "yellow-50", "dark": "yellow-900"},
                "children": [
                    {
                        "type": "Row",
                        "align": "center",
                        "children": [
                            {
                                "type": "Title",
                                "value": "C A L I F O R N I A",
                                "size": "sm",
                                "weight": "bold",
                                "color": {"light": "orange-700", "dark": "orange-100"},
                            },
                            {"type": "Spacer"},
                            {
                                "type": "Badge",
                                "label": "meowing license",
                                "color": "warning",
                                "variant": "soft",
                            },
                        ],
                    }
                ],
            },
            {
                "type": "Row",
                "padding": {"x": 5, "top": 2, "bottom": 4},
                "gap": 4,
                "align": "start",
                "children": [
                    {
                        "type": "Box",
                        "background": "linear-gradient(135deg, #fff6d9 0%, #ceb0fb 100%)",
                        "radius": "3xl",
                        "align": "center",
                        "justify": "center",
                        "children": [
                            {
                                "type": "Image",
                                "src": _image_src(state),
                                "width": 90,
                                "height": 110,
                                "position": "top",
                                "radius": "3xl",
                            }
                        ],
                    },
                    {
                        "type": "Col",
                        "gap": 2,
                        "flex": "auto",
                        "children": [
                            {
                                "type": "Title",
                                "value": state.name,
                                "size": "md",
                            },
                            {
                                "type": "Row",
                                "children": [
                                    {"type": "Caption", "value": "Age"},
                                    {"type": "Spacer"},
                                    {
                                        "type": "Text",
                                        "value": _format_age_label(state.age),
                                        "size": "sm",
                                        "textAlign": "end",
                                    },
                                ],
                            },
                            {
                                "type": "Row",
                                "children": [
                                    {"type": "Caption", "value": "Color pattern"},
                                    {"type": "Spacer"},
                                    {
                                        "type": "Text",
                                        "value": _format_color_pattern_label(state.color_pattern),
                                        "size": "sm",
                                        "textAlign": "end",
                                    },
                                ],
                            },
                            {
                                "type": "Row",
                                "children": [
                                    {"type": "Caption", "value": "Toy choice"},
                                    {"type": "Spacer"},
                                    {
                                        "type": "Text",
                                        "value": _format_favorite_toy(favorite_toy),
                                        "size": "sm",
                                        "textAlign": "end",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    }
    return Card.model_validate(widget_data)


def profile_widget_copy_text(state: CatState) -> str:
    return f"{state.name}, age {state.age}, is a {state.color_pattern} cat."
