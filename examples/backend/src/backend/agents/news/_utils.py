"""
Utilities for bridging ADK and OpenAI Agent SDK patterns.

This module provides helpers for two key differences between ADK and OpenAI Agent SDK:

1. **Instruction Template Variables**: ADK interprets {variable} patterns in instructions
   as template variables requiring session state injection. Use `escape_instruction_templates()`
   to escape these patterns when they're just examples, not actual variables.

2. **Complex Pydantic Types in Tool Signatures**: ADK cannot automatically parse complex
   Pydantic types like `List[ArticleMetadata]` in function signatures. Additionally, LLMs
   often drop fields when passing data between tool calls (this is LLM behavior, not
   framework-specific). Use `SearchResultCache` to transparently handle this by caching
   full data server-side and passing only IDs through the LLM.

These utilities may be promoted to adk-chatkit once patterns are validated.
"""

from __future__ import annotations

import re
from typing import Any, TypeVar

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


# =============================================================================
# INSTRUCTION TEMPLATE UTILITIES
# =============================================================================


def escape_instruction_templates(instruction: str) -> str:
    """
    Escape {variable} patterns in instructions so ADK doesn't treat them as template variables.

    ADK interprets {variable} patterns as template variables that need to be injected
    from session state. When your instructions contain example patterns like {article_id}
    or {author}, use this function to escape them to {{article_id}} or {{author}}.

    Args:
        instruction: The instruction string with {variable} patterns

    Returns:
        Instruction with patterns escaped as {{variable}}
    """
    # Match {word} but not {{word}} (already escaped)
    pattern = r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})"
    return re.sub(pattern, r"{{\1}}", instruction)


# =============================================================================
# SEARCH RESULT CACHE
# =============================================================================


class SearchResultCache:
    """
    Cache for search results that handles the LLM field-dropping problem.

    When LLMs pass data between tool calls, they often drop fields.
    This cache stores full data server-side and passes only IDs through the LLM.

    Usage:
        # In search function
        cache = SearchResultCache("articles")
        return cache.store_and_summarize(tool_context, articles, ["id", "title"])

        # In widget function
        cache = SearchResultCache("articles")
        articles = cache.retrieve(tool_context, article_ids, ArticleMetadata)
    """

    def __init__(self, cache_key: str) -> None:
        self.cache_key = f"_cache_{cache_key}"

    def store(
        self,
        tool_context: ToolContext,
        items: list[dict[str, Any]],
        id_field: str = "id",
    ) -> list[str]:
        """Store items in cache and return their IDs."""
        cache: dict[str, Any] = tool_context.state.setdefault(self.cache_key, {})
        item_ids: list[str] = []
        for item in items:
            item_id = str(item.get(id_field, ""))
            if item_id:
                cache[item_id] = item
                item_ids.append(item_id)
        return item_ids

    def store_and_summarize(
        self,
        tool_context: ToolContext,
        items: list[dict[str, Any]],
        summary_fields: list[str] | None = None,
        id_field: str = "id",
        ids_key: str = "item_ids",
        items_key: str = "items",
    ) -> dict[str, Any]:
        """Store items and return a summarized response for the LLM."""
        if summary_fields is None:
            summary_fields = [id_field, "title"]
        elif id_field not in summary_fields:
            summary_fields = [id_field, *summary_fields]

        item_ids = self.store(tool_context, items, id_field)
        summaries = [{f: item.get(f) for f in summary_fields if f in item} for item in items]

        return {"count": len(items), ids_key: item_ids, items_key: summaries}

    def retrieve(
        self,
        tool_context: ToolContext,
        item_ids: list[str],
        model_class: type[T],
    ) -> list[T]:
        """Retrieve items from cache and validate to Pydantic models."""
        cache: dict[str, Any] = tool_context.state.get(self.cache_key, {})
        items = [cache[item_id] for item_id in item_ids if item_id in cache]
        return [model_class.model_validate(item) for item in items]

    def get(self, tool_context: ToolContext, item_id: str) -> dict[str, Any] | None:
        """Get a single cached item by ID."""
        cache: dict[str, Any] = tool_context.state.get(self.cache_key, {})
        result: dict[str, Any] | None = cache.get(item_id)
        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def prepare_search_response(
    items: list[dict[str, Any]],
    tool_context: ToolContext,
    cache_key: str,
    summary_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Prepare article search response with caching."""
    cache = SearchResultCache(cache_key)
    return cache.store_and_summarize(
        tool_context,
        items,
        summary_fields=summary_fields or ["id", "title"],
        ids_key="article_ids",
        items_key="articles",
    )


def prepare_event_search_response(
    events: list[dict[str, Any]],
    tool_context: ToolContext,
    cache_key: str,
) -> dict[str, Any]:
    """Prepare event search response with caching."""
    cache = SearchResultCache(cache_key)
    return cache.store_and_summarize(
        tool_context,
        events,
        summary_fields=["id", "title", "date"],
        ids_key="event_ids",
        items_key="events",
    )


def validate_cached_items(
    tool_context: ToolContext,
    cache_key: str,
    item_ids: list[str],
    model_class: type[T],
) -> list[T]:
    """Retrieve and validate cached items."""
    cache = SearchResultCache(cache_key)
    return cache.retrieve(tool_context, item_ids, model_class)
