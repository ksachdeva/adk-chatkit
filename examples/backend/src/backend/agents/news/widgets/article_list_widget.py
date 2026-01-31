"""
Defines a presentation widget that highlights a list of articles using the
same layout cues as the featured article card in the Newsroom panel.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from chatkit.widgets import ListView, WidgetRoot

from ..data.article_store import ArticleMetadata


def _format_date(value: datetime) -> str:
    month = value.strftime("%b")
    return f"{month} {value.day}, {value.year}"


def build_article_list_widget(articles: list[ArticleMetadata]) -> WidgetRoot:
    """Render an article list widget programmatically."""
    items = []

    for article in articles:
        item_data: dict[str, Any] = {
            "type": "ListViewItem",
            "key": article.id,
            "onClickAction": {
                "type": "open_article",
                "handler": "client",
                "payload": {"id": article.id},
            },
            "children": [
                {
                    "type": "Row",
                    "gap": 3,
                    "children": [
                        {
                            "type": "Box",
                            "radius": "lg",
                            "overflow": "hidden",
                            "width": 120,
                            "height": 80,
                            "flex": "none",
                            "children": [
                                {
                                    "type": "Image",
                                    "src": article.heroImageUrl,
                                    "width": 120,
                                    "height": 80,
                                }
                            ],
                        },
                        {
                            "type": "Col",
                            "gap": 1,
                            "flex": "auto",
                            "justify": "center",
                            "children": [
                                {
                                    "type": "Text",
                                    "value": article.title,
                                    "weight": "semibold",
                                    "maxLines": 2,
                                },
                                {
                                    "type": "Row",
                                    "gap": 2,
                                    "children": [
                                        {
                                            "type": "Caption",
                                            "value": article.author,
                                        },
                                        {
                                            "type": "Caption",
                                            "value": "·",
                                        },
                                        {
                                            "type": "Caption",
                                            "value": _format_date(article.date),
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                }
            ],
        }
        items.append(item_data)

    widget_data = {"type": "ListView", "children": items}
    return ListView.model_validate(widget_data)
