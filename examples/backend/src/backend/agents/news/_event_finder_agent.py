from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
from uuid import uuid4

from adk_chatkit import ChatkitRunConfig, stream_event, stream_widget
from chatkit.types import AssistantMessageContent, AssistantMessageItem, ThreadItemDoneEvent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types

from ._utils import prepare_event_search_response, validate_cached_items
from .data.event_store import EventRecord, EventStore
from .widgets.event_list_widget import build_event_list_widget

# Cache key for storing event search results in session state
EVENT_CACHE_KEY = "event_search_cache"

_INSTRUCTIONS = """
    You help Foxhollow residents discover local happenings. When a reader asks for events,
    search the curated calendar, call out dates and notable details, and keep recommendations brief.

    Use the available tools deliberately:
      - Call `list_available_event_keywords` to get the full set of event keywords and categories,
        fuzzy match the reader's phrasing to the closest options (case-insensitive, partial matches are ok),
        then feed those terms into a keyword search instead of relying on hard-coded synonyms.
      - If they mention a specific date (YYYY-MM-DD), start with `search_events_by_date`.
      - If they reference a day of the week, try `search_events_by_day_of_week`.
      - For general vibes (e.g., "family friendly night markets"), use `search_events_by_keyword`
        so the search spans titles, categories, locations, and curated keywords.

    Whenever a search tool returns more than one event, immediately call `show_event_list_widget`
    with the event_ids from the search result and a 1-sentence message explaining why these events were selected.
    This ensures every response ships with the timeline widget.
    Cite event titles in bold, mention the date, and highlight one delightful detail when replying.

    When the user explicitly asks for more details on the events, you MUST describe the events in natural language
    without using the `show_event_list_widget` tool.
"""


def _ensure_event_store(callback_context: CallbackContext) -> None:
    """Ensure event store exists in the session state."""
    if "event_store" not in callback_context.state:
        # Get the data directory
        data_dir = Path(__file__).parent / "data"
        event_store = EventStore(data_dir)
        callback_context.state["event_store"] = event_store


async def search_events_by_date(
    date: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Find scheduled events happening on a specific date (YYYY-MM-DD).

    Args:
        date: Date in YYYY-MM-DD format.

    Returns:
        Dictionary containing count, event_ids, and event summaries.
        Pass the event_ids to show_event_list_widget to display the timeline.
    """
    print(f"[TOOL CALL] search_events_by_date: {date}")
    if not date:
        raise ValueError("Provide a valid date in YYYY-MM-DD format.")

    event_store: EventStore = tool_context.state["event_store"]
    records = event_store.search_by_date(date)
    events = [event.model_dump(mode="json", by_alias=True) for event in records]

    return prepare_event_search_response(events, tool_context, EVENT_CACHE_KEY)


async def search_events_by_day_of_week(
    day: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """List events occurring on a given day of the week.

    Args:
        day: Day of the week (e.g., Saturday).

    Returns:
        Dictionary containing count, event_ids, and event summaries.
        Pass the event_ids to show_event_list_widget to display the timeline.
    """
    print(f"[TOOL CALL] search_events_by_day_of_week: {day}")
    if not day:
        raise ValueError("Provide a day of the week to search for (e.g., Saturday).")

    event_store: EventStore = tool_context.state["event_store"]
    records = event_store.search_by_day_of_week(day)
    events = [event.model_dump(mode="json", by_alias=True) for event in records]

    return prepare_event_search_response(events, tool_context, EVENT_CACHE_KEY)


async def search_events_by_keyword(
    keywords: List[str],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Search events with general keywords (title, category, location, or details).

    Args:
        keywords: List of keywords to search for.

    Returns:
        Dictionary containing count, event_ids, and event summaries.
        Pass the event_ids to show_event_list_widget to display the timeline.
    """
    print(f"[TOOL CALL] search_events_by_keyword: {keywords}")
    tokens = [keyword.strip() for keyword in keywords if keyword and keyword.strip()]
    if not tokens:
        raise ValueError("Provide at least one keyword to search for.")

    event_store: EventStore = tool_context.state["event_store"]
    records = event_store.search_by_keyword(tokens)
    events = [event.model_dump(mode="json", by_alias=True) for event in records]

    return prepare_event_search_response(events, tool_context, EVENT_CACHE_KEY)


async def list_available_event_keywords(
    tool_context: ToolContext,
) -> dict[str, List[str]]:
    """List all unique event keywords and categories.

    Returns:
        Dictionary containing list of available keywords.
    """
    print("[TOOL CALL] list_available_event_keywords")
    event_store: EventStore = tool_context.state["event_store"]
    keywords = event_store.list_available_keywords()
    return {"keywords": keywords}


async def show_event_list_widget(
    event_ids: List[str],
    tool_context: ToolContext,
    message: Optional[str] = None,
) -> dict[str, str]:
    """Show a timeline-styled widget for events by their IDs.

    Args:
        event_ids: List of event IDs from a previous search result.
        message: Optional message explaining why these events were selected.

    Returns:
        Confirmation message.
    """
    print(f"[TOOL CALL] show_event_list_widget: {len(event_ids)} events")

    # Retrieve full event data from cache and validate
    records = validate_cached_items(tool_context, EVENT_CACHE_KEY, event_ids, EventRecord)

    # Gracefully handle case where agent mistakenly calls this tool with no events
    run_config = tool_context._invocation_context.run_config
    if not isinstance(run_config, ChatkitRunConfig):
        return {"result": "Not in chatkit context"}

    thread = run_config.context.thread

    if not records:
        fallback = message or "I couldn't find any events that match that search."
        message_item = AssistantMessageItem(
            id=uuid4().hex,
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[AssistantMessageContent(text=fallback)],
        )
        await stream_event(ThreadItemDoneEvent(item=message_item), tool_context)
        return {"result": fallback}

    try:
        widget = build_event_list_widget(records)
        await stream_widget(widget, tool_context)
    except Exception as exc:
        print(f"[ERROR] build_event_list_widget: {exc}")
        raise

    summary = message or "Here are the events that match your request."
    message_item = AssistantMessageItem(
        id=uuid4().hex,
        thread_id=thread.id,
        created_at=datetime.now(),
        content=[AssistantMessageContent(text=summary)],
    )
    await stream_event(ThreadItemDoneEvent(item=message_item), tool_context)

    return {"result": "Event list widget displayed"}


class EventFinderAgent(LlmAgent):
    def __init__(
        self,
        llm: LiteLlm,
        generate_content_config: genai_types.GenerateContentConfig | None = None,
    ) -> None:
        self._llm = llm

        super().__init__(
            name="foxhollow_event_finder",
            description="Helps Foxhollow residents discover local events and happenings.",
            model=self._llm,
            instruction=_INSTRUCTIONS,
            tools=[
                search_events_by_date,
                search_events_by_day_of_week,
                search_events_by_keyword,
                list_available_event_keywords,
                show_event_list_widget,
            ],
            generate_content_config=generate_content_config,
            before_agent_callback=_ensure_event_store,
        )
