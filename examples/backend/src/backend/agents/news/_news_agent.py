from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adk_chatkit import ChatkitRunConfig, stream_event, stream_widget
from chatkit.types import AssistantMessageContent, AssistantMessageItem, ThreadItemDoneEvent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types

from ._utils import prepare_search_response, validate_cached_items
from .data.article_store import ArticleMetadata, ArticleRecord, ArticleStore
from .widgets.article_list_widget import build_article_list_widget

# Cache key for storing article search results in session state
ARTICLE_CACHE_KEY = "article_search_cache"

_INSTRUCTIONS = """
    You are News Guide, a service-forward assistant focused on helping readers quickly
    discover the most relevant news for their needs. Prioritize clarity, highlight how
    each story serves the reader, and keep answers concise with skimmable structure.

    Before recommending or summarizing, always consult the latest article metadata via
    the available tools.

    If the reader provides desired topics, locations, or tags, filter results before responding
    and call out any notable gaps.

    Unless the reader explicitly asks for a set number of articles, default to suggesting 2 articles.

    When the reader references "this article," "this story," or "this page," treat that as a request
    about the currently open article. Load it with `get_current_page`, review the content, and answer
    their question directly using specific details instead of asking them to copy anything over.

    When summarizing:
      - Cite the article title.
      - The summary should be 2-4 sentences long.
      - Do NOT explicitly mention the word "summary" in your response.
      - After summarizing, ask the reader if they have any questions about the article.

    Formatting output:
      - Default to italicizing article titles when you mention them, and wrap any direct excerpts from the article content in
        Markdown blockquotes so they stand out.
      - Add generous paragraph breaks for readability.

    Use the tools deliberately:
      - Call `list_available_tags_and_keywords` to get a list of all unique tags and keywords available to search by. Fuzzy match
        the reader's phrasing to these tags/keywords (case-insensitive, partial matches are ok) and pick the closest ones—instead
        of relying on any hard-coded synonym map—before running a search.
      - Use `get_current_page` to fetch the full article the reader currently has open whenever they need deeper details
        or ask questions about "this page".
      - Use `search_articles_by_tags` only when the reader explicitly references tags/sections (e.g., "show me everything tagged parks"); otherwise skip it.
      - Default to `search_articles_by_keywords` to match metadata (titles, subtitles, tags, keywords) to the reader's asks.
      - Use `search_articles_by_exact_text` when the reader quote a phrase or wants an exact content match.
      - After running a search, you will receive article_ids in the response. Pass these article_ids to `show_article_list_widget`
        along with a message explaining why these articles were selected.
      - If the reader explicitly asks about events, happenings, or things to do, call `delegate_to_event_finder`
        with their request so the Foxhollow Event Finder agent can take over.
      - If the reader wants a Foxhollow-flavored puzzle, coffee-break brain teaser, or mentions the puzzle tool,
        call `delegate_to_puzzle_keeper` so the Foxhollow Puzzle Keeper can lead with Two Truths and the mini crossword.

    Custom tags:
     - When you see an <ARTICLE_REFERENCE> tag with an article ID in the context, call `get_article_by_id`
       with that id before citing details so your answer can reference the tagged article accurately.
     - When you see an <AUTHOR_REFERENCE> tag with an author name in the context, or the reader names an author,
       call `search_articles_by_author` with that author before recommending pieces so you feature their work first.

    Suggest a next step—such as related articles or follow-up angles—whenever it adds value.
"""

FEATURED_PAGE_ID = "featured"


def _ensure_article_store(callback_context: CallbackContext) -> None:
    """Ensure article store exists in the session state."""
    if "article_store" not in callback_context.state:
        data_dir = Path(__file__).parent / "data"
        article_store = ArticleStore(data_dir)
        callback_context.state["article_store"] = article_store


async def search_articles_by_tags(
    tags: List[str],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """List newsroom articles, optionally filtered by tags.

    Args:
        tags: One or more tags to filter by.

    Returns:
        Dictionary containing count, article_ids, and article summaries.
        Pass the article_ids to show_article_list_widget to display the full list.
    """
    print(f"[TOOL CALL] search_articles_by_tags {tags}")
    if not tags:
        raise ValueError("Please provide at least one tag to search for.")
    tags = [tag.strip().lower() for tag in tags if tag and tag.strip()]

    article_store: ArticleStore = tool_context.state["article_store"]
    records = article_store.list_metadata_for_tags(tags)
    # Serialize to JSON-compatible dicts (records are ArticleMetadata objects)
    articles = [article.model_dump(mode="json") for article in records]

    # Cache full data and return summaries
    response = prepare_search_response(articles, tool_context, ARTICLE_CACHE_KEY)
    response["tags"] = tags
    return response


async def search_articles_by_author(
    author: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Find articles written by a specific author.

    Args:
        author: Author name to search for (case-insensitive).

    Returns:
        Dictionary containing author, count, article_ids, and article summaries.
        Pass the article_ids to show_article_list_widget to display the full list.
    """
    author = author.strip()
    print(f"[TOOL CALL] search_articles_by_author {author}")
    if not author:
        raise ValueError("Please provide an author name to search for.")

    article_store: ArticleStore = tool_context.state["article_store"]
    records = article_store.search_metadata_by_author(author)
    # Validate and serialize to JSON-compatible dicts
    articles = [ArticleMetadata.model_validate(record).model_dump(mode="json") for record in records]

    # Cache full data and return summaries
    response = prepare_search_response(articles, tool_context, ARTICLE_CACHE_KEY)
    response["author"] = author
    return response


async def list_available_tags_and_keywords(
    tool_context: ToolContext,
) -> dict[str, List[str]]:
    """List all unique tags and keywords available across the newsroom archive. No parameters.

    Returns:
        Dictionary containing sorted lists of tags and keywords.
    """
    print("[TOOL CALL] list_available_tags_and_keywords")
    article_store: ArticleStore = tool_context.state["article_store"]
    return article_store.list_available_tags_and_keywords()


async def search_articles_by_keywords(
    keywords: List[str],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Search newsroom articles by keywords within their metadata (title, tags, keywords, etc.).

    Args:
        keywords: List of keywords to match against metadata.

    Returns:
        Dictionary containing count, article_ids, and article summaries.
        Pass the article_ids to show_article_list_widget to display the full list.
    """
    cleaned = [keyword.strip().lower() for keyword in keywords if keyword and keyword.strip()]
    print(f"[TOOL CALL] search_articles_by_keywords {cleaned}")
    if not cleaned:
        raise ValueError("Please provide at least one non-empty keyword to search for.")

    article_store: ArticleStore = tool_context.state["article_store"]
    records = article_store.search_metadata_by_keywords(cleaned)
    # Validate and serialize to JSON-compatible dicts
    articles = [ArticleMetadata.model_validate(record).model_dump(mode="json") for record in records]

    # Cache full data and return summaries
    response = prepare_search_response(articles, tool_context, ARTICLE_CACHE_KEY)
    response["keywords"] = cleaned
    return response


async def search_articles_by_exact_text(
    text: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Search newsroom articles for an exact text match within their content.

    Args:
        text: Exact string to find inside article bodies.

    Returns:
        Dictionary containing count, article_ids, and article summaries.
        Pass the article_ids to show_article_list_widget to display the full list.
    """
    trimmed = text.strip()
    print(f"[TOOL CALL] search_articles_by_exact_text {trimmed}")
    if not trimmed:
        raise ValueError("Please provide a non-empty text string to search for.")

    article_store: ArticleStore = tool_context.state["article_store"]
    records = article_store.search_content_by_exact_text(trimmed)
    # Validate and serialize to JSON-compatible dicts
    articles = [ArticleMetadata.model_validate(record).model_dump(mode="json") for record in records]

    # Cache full data and return summaries
    response = prepare_search_response(articles, tool_context, ARTICLE_CACHE_KEY)
    response["text"] = trimmed
    return response


async def get_article_by_id(
    article_id: str,
    tool_context: ToolContext,
) -> dict[str, dict[str, Any]]:
    """Fetch the markdown content for a specific article.

    Args:
        article_id: Identifier of the article to load.

    Returns:
        Dictionary containing the full article record.
    """
    print(f"[TOOL CALL] get_article_by_id {article_id}")
    article_store: ArticleStore = tool_context.state["article_store"]
    record = article_store.get_article(article_id)
    if not record:
        raise ValueError(f"Article '{article_id}' does not exist.")
    return {"article": record}


async def get_current_page(
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Load the full content for the page the reader currently has open. No parameters.

    Returns:
        Dictionary containing page type, articles, and optionally article_id.
    """
    print("[TOOL CALL] get_current_page")

    # Get article_id from run_config context if available
    run_config = tool_context._invocation_context.run_config
    article_id = None
    if isinstance(run_config, ChatkitRunConfig):
        article_id = getattr(run_config.context, "article_id", None)

    if not article_id:
        article_id = FEATURED_PAGE_ID

    article_store: ArticleStore = tool_context.state["article_store"]
    page_type, articles = _load_current_page_records(article_store, article_id)

    payload = {
        "page": page_type,
        "articles": [article.model_dump() for article in articles],
    }
    if page_type != FEATURED_PAGE_ID:
        payload["article_id"] = article_id

    return payload


async def show_article_list_widget(
    article_ids: List[str],
    message: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Show a Newsroom-style article list widget for articles by their IDs.

    Args:
        article_ids: List of article IDs from a previous search result.
        message: Introductory text explaining why these were selected.

    Returns:
        Confirmation message.
    """
    print(f"[TOOL CALL] show_article_list_widget {len(article_ids)} articles")
    if not article_ids:
        raise ValueError("Provide at least one article ID before calling this tool.")

    run_config = tool_context._invocation_context.run_config
    if not isinstance(run_config, ChatkitRunConfig):
        return {"result": "Not in chatkit context"}

    thread = run_config.context.thread

    try:
        # Send message first
        message_item = AssistantMessageItem(
            id=uuid4().hex,
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[AssistantMessageContent(text=message)],
        )
        await stream_event(ThreadItemDoneEvent(item=message_item), tool_context)

        # Retrieve full article data from cache and validate
        article_objects = validate_cached_items(tool_context, ARTICLE_CACHE_KEY, article_ids, ArticleMetadata)

        if not article_objects:
            return {"result": "No articles found in cache. Run a search first."}

        widget = build_article_list_widget(article_objects)
        await stream_widget(widget, tool_context)

        return {"result": f"Article list widget displayed with {len(article_objects)} articles"}
    except Exception as exc:
        print(f"[ERROR] show_article_list_widget: {exc}")
        raise


def _load_featured_articles(store: ArticleStore) -> list[ArticleRecord]:
    """Load all featured articles."""
    metadata_entries = store.list_metadata_for_tags([FEATURED_PAGE_ID])
    articles: list[ArticleRecord] = []
    seen: set[str] = set()

    for entry in metadata_entries:
        article_id = entry.id
        if not article_id or article_id in seen:
            continue

        record = store.get_article(article_id)
        if record:
            articles.append(ArticleRecord.model_validate(record))
            seen.add(article_id)

    return articles


def _load_current_page_records(store: ArticleStore, article_id: str) -> tuple[str, list[ArticleRecord]]:
    """Load records for the current page."""
    if article_id == FEATURED_PAGE_ID:
        articles = _load_featured_articles(store)
        if not articles:
            raise ValueError("Unable to locate any featured articles to load.")
        return FEATURED_PAGE_ID, articles

    record = store.get_article(article_id)
    if not record:
        raise ValueError(f"Article '{article_id}' does not exist.")
    return "article", [ArticleRecord.model_validate(record)]


class NewsAgent(LlmAgent):
    def __init__(
        self,
        llm: LiteLlm,
        generate_content_config: genai_types.GenerateContentConfig | None = None,
    ) -> None:
        self._llm = llm

        super().__init__(
            name="foxhollow_dispatch_news_guide",
            description="A service-forward assistant helping readers discover relevant news.",
            model=self._llm,
            instruction=_INSTRUCTIONS,
            tools=[
                # Simple retrieval tools
                list_available_tags_and_keywords,
                get_article_by_id,
                get_current_page,
                # Search tools
                search_articles_by_author,
                search_articles_by_tags,
                search_articles_by_keywords,
                search_articles_by_exact_text,
                # Presentation tools
                show_article_list_widget,
            ],
            generate_content_config=generate_content_config,
            before_agent_callback=_ensure_article_store,
        )
