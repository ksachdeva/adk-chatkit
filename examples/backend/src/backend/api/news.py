"""News API endpoints."""

import json
from pathlib import Path
from typing import Any

import aiofiles
from adk_chatkit import ADKContext
from chatkit.server import StreamingResult
from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from starlette.responses import JSONResponse

from backend._config import Settings
from backend.agents.news import NewsChatKitServer

router = APIRouter(route_class=DishkaRoute)


class NewsADKContext(ADKContext):
    """Extended context for news API with article_id support."""

    article_id: str | None = None


# Load articles and events data from the agents/news/data directory
DATA_DIR = Path(__file__).parent.parent / "agents" / "news" / "data"
ARTICLES_FILE = DATA_DIR / "articles.json"
EVENTS_FILE = DATA_DIR / "events.json"

# Cache for articles data
_articles_cache: list[dict[str, Any]] | None = None
_articles_by_id_cache: dict[str, dict[str, Any]] | None = None


async def _load_articles() -> list[dict[str, Any]]:
    """Load and cache articles from JSON file."""
    global _articles_cache, _articles_by_id_cache

    if _articles_cache is None:
        async with aiofiles.open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            articles = json.loads(content)
            # articles.json is a list directly, not {"articles": [...]}
            _articles_cache = articles if isinstance(articles, list) else []
            _articles_by_id_cache = {article["id"]: article for article in _articles_cache}

    return _articles_cache if _articles_cache is not None else []


async def _get_article_by_id(article_id: str) -> dict[str, Any] | None:
    """Get a single article by ID from cache."""
    await _load_articles()  # Ensure cache is populated
    return _articles_by_id_cache.get(article_id) if _articles_by_id_cache else None


async def _load_article_content(article_id: str) -> str:
    """Load article content from markdown file."""
    content_file = DATA_DIR / "articles" / f"{article_id}.md"
    if not content_file.exists():
        return ""

    async with aiofiles.open(content_file, "r", encoding="utf-8") as f:
        content = str(await f.read())
        return content


@router.get("/articles")
async def get_articles() -> dict[str, Any]:
    """Get all articles."""
    articles = await _load_articles()
    return {"articles": articles}


@router.get("/articles/{article_id}")
async def get_article(article_id: str) -> dict[str, Any]:
    """Get a single article by ID with full content."""
    article = await _get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail=f"Article {article_id} not found")

    # Load full content
    content = await _load_article_content(article_id)

    # Return article with content
    return {
        **article,
        "content": content,
    }


@router.get("/events")
async def get_events() -> dict[str, Any]:
    """Get all events."""
    async with aiofiles.open(EVENTS_FILE, "r", encoding="utf-8") as f:
        content = await f.read()
        events = json.loads(content)

    # events.json is a list directly, not {"events": [...]}
    return {"events": events if isinstance(events, list) else []}


@router.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    settings: FromDishka[Settings],
    request_server: FromDishka[NewsChatKitServer],
) -> Response:
    """ChatKit endpoint for news assistant."""
    payload = await request.body()

    user_id = "ksachdeva-1"

    # Extract article-id from request headers
    article_id = request.headers.get("article-id")

    result = await request_server.process(
        payload,
        NewsADKContext(
            user_id=user_id,
            app_name=settings.NEWS_APP_NAME,
            article_id=article_id,
        ),
    )

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


@router.get("/health", summary="Check health of news agent")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
