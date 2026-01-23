"""Metro map context for passing store to tools."""

from __future__ import annotations

from typing import Any

from adk_chatkit import ADKAgentContext


class MetroMapAgentContext(ADKAgentContext):
    """Agent context with metro map store for tools to access."""

    metro_map_store: Any = None

    class Config:
        arbitrary_types_allowed = True
