from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from adk_chatkit import ADKAgentContext, ADKChatKitServer, ADKContext, ADKStore, ChatkitRunConfig, stream_agent_response
from chatkit.actions import Action
from chatkit.types import (
    ThreadItemUpdated,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
    WidgetItem,
    WidgetRootUpdated,
)
from google.adk.agents.run_config import StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types as genai_types

from backend._config import Settings
from backend._runner_manager import RunnerManager

from ._event_finder_agent import EventFinderAgent
from ._news_agent import NewsAgent
from ._puzzle_agent import PuzzleAgent
from ._title_agent import TitleAgent
from .data.article_store import ArticleStore
from .data.event_store import EventRecord, EventStore
from .widgets.event_list_widget import build_event_list_widget


class NewsAgentContext(ADKAgentContext):
    """Extended context for news agent with article_id support."""

    article_id: Optional[str] = None


def _make_news_agent(settings: Settings) -> NewsAgent:
    return NewsAgent(
        llm=LiteLlm(
            model=settings.gpt41_mini_agent.llm.model_name,
            **settings.gpt41_mini_agent.llm.provider_args,
        ),
        generate_content_config=settings.gpt41_mini_agent.generate_content,
    )


def _make_event_finder_agent(settings: Settings) -> EventFinderAgent:
    return EventFinderAgent(
        llm=LiteLlm(
            model=settings.gpt41_mini_agent.llm.model_name,
            **settings.gpt41_mini_agent.llm.provider_args,
        ),
        generate_content_config=settings.gpt41_mini_agent.generate_content,
    )


def _make_puzzle_agent(settings: Settings) -> PuzzleAgent:
    return PuzzleAgent(
        llm=LiteLlm(
            model=settings.gpt41_mini_agent.llm.model_name,
            **settings.gpt41_mini_agent.llm.provider_args,
        ),
        generate_content_config=settings.gpt41_mini_agent.generate_content,
    )


def _make_title_agent(settings: Settings) -> TitleAgent:
    return TitleAgent(
        llm=LiteLlm(
            model=settings.gpt41_mini_agent.llm.model_name,
            **settings.gpt41_mini_agent.llm.provider_args,
        ),
        generate_content_config=settings.gpt41_mini_agent.generate_content,
    )


def _user_message_text(item: UserMessageItem) -> str:
    parts: list[str] = []
    for part in item.content:
        text = getattr(part, "text", None)
        if text:
            parts.append(text)
    return " ".join(parts).strip()


class NewsChatKitServer(ADKChatKitServer):
    def __init__(
        self,
        store: ADKStore,
        session_service: BaseSessionService,
        runner_manager: RunnerManager,
        settings: Settings,
    ) -> None:
        super().__init__(store)
        self._store = store
        self._session_service = session_service
        self._settings = settings

        # Create data stores
        data_dir = Path(__file__).parent / "data"
        self.article_store = ArticleStore(data_dir)
        self.event_store = EventStore(data_dir)

        # Create agents
        news_agent = _make_news_agent(settings)
        event_finder_agent = _make_event_finder_agent(settings)
        puzzle_agent = _make_puzzle_agent(settings)
        title_agent = _make_title_agent(settings)

        # Create runners for each agent with unique app names
        # Each runner manages its own session storage namespace, but they share thread metadata
        # through the common store. This allows clean delegation without context pollution.
        base_app_name = settings.NEWS_APP_NAME
        self._news_runner = runner_manager.add_runner(base_app_name, news_agent)
        self._news_runner_app_name = base_app_name

        self._event_runner = runner_manager.add_runner(f"{base_app_name}_events", event_finder_agent)
        self._event_runner_app_name = f"{base_app_name}_events"

        self._puzzle_runner = runner_manager.add_runner(f"{base_app_name}_puzzle", puzzle_agent)
        self._puzzle_runner_app_name = f"{base_app_name}_puzzle"

        self._title_runner = runner_manager.add_runner(f"{base_app_name}_title", title_agent)
        self._title_runner_app_name = f"{base_app_name}_title"

    async def _run_agent_with_message(
        self,
        thread: ThreadMetadata,
        message: str,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Helper to run the news agent with a message string."""
        # Extract article_id from context if available
        article_id = getattr(context, "article_id", None)

        agent_context = NewsAgentContext(
            app_name=self._news_runner_app_name,
            user_id=context.user_id,
            thread=thread,
            article_id=article_id,
        )

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=message)],
        )

        event_stream = self._news_runner.run_async(
            user_id=context.user_id,
            session_id=thread.id,
            new_message=content,
            run_config=ChatkitRunConfig(streaming_mode=StreamingMode.SSE, context=agent_context),
        )

        async for event in stream_agent_response(agent_context, event_stream):
            yield event

    async def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle widget actions."""
        if action.type == "open_article":
            async for event in self._handle_open_article_action(thread, action, context):
                yield event
            return
        if action.type == "view_event_details":
            async for event in self._handle_view_event_details_action(action, sender):
                yield event
            return

    async def _handle_open_article_action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle opening an article."""
        article_id = action.payload.get("id")
        if not article_id:
            return

        metadata = self.article_store.get_metadata(article_id)
        title = metadata["title"] if metadata else None
        message_text = f"[HIDDEN]\nUser opened article: {article_id}"
        if title:
            message_text += f" (title: {title})"

        async for event in self._run_agent_with_message(thread, message_text, context):
            yield event

    async def _handle_view_event_details_action(
        self,
        action: Action[str, Any],
        sender: WidgetItem | None,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle viewing event details."""
        selected_event_id = action.payload.get("id")
        event_ids = action.payload.get("eventIds", [])

        if not selected_event_id or not event_ids or not sender:
            return

        record = self.event_store.get_event(selected_event_id)
        if not record:
            return

        # Rebuild widget with selected event
        records: list[EventRecord] = []
        for event_id in event_ids:
            event_record = self.event_store.get_event(event_id)
            if event_record:
                records.append(event_record)

        updated_widget = build_event_list_widget(records, selected_event_id=selected_event_id)

        yield ThreadItemUpdated(
            item_id=sender.id,
            update=WidgetRootUpdated(widget=updated_widget),
        )

    async def _adk_respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        if item is None:
            return

        message_text = _user_message_text(item)
        if not message_text:
            return

        # Update thread title if needed (in background)
        if thread.title is None:
            await self._maybe_update_thread_title(thread, message_text, context)

        # Select which agent to use
        runner, runner_app_name = self._select_runner(item)

        # Extract article_id from context if available
        article_id = getattr(context, "article_id", None)

        # Create agent context with the runner's app_name to ensure session lookup works correctly
        agent_context = NewsAgentContext(
            app_name=runner_app_name,  # Use the runner's app_name, not the generic context.app_name
            user_id=context.user_id,
            thread=thread,
            article_id=article_id,
        )

        # Run the agent
        event_stream = runner.run_async(
            user_id=context.user_id,
            session_id=thread.id,
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=message_text)],
            ),
            run_config=ChatkitRunConfig(streaming_mode=StreamingMode.SSE, context=agent_context),
        )

        async for event in stream_agent_response(agent_context, event_stream):
            yield event

    async def _maybe_update_thread_title(self, thread: ThreadMetadata, message_text: str, context: ADKContext) -> None:
        """Generate and update thread title using the title agent."""
        # TODO: Implement async title generation
        # For now, use a simple default title
        try:
            if len(message_text) > 50:
                title = message_text[:47] + "..."
            else:
                title = message_text
            thread.title = title.strip()
            await self._store.save_thread(thread, context)
        except Exception as exc:
            print(f"[ERROR] Failed to update thread title: {exc}")

    def _select_runner(self, item: UserMessageItem | None) -> tuple[Any, str]:
        """Select which agent runner to use based on tool choice.

        Returns:
            tuple[Runner, str]: The runner and its app_name for session management.
        """
        tool_choice = self._resolve_tool_choice(item)
        if tool_choice == "delegate_to_event_finder":
            return self._event_runner, self._event_runner_app_name
        if tool_choice == "delegate_to_puzzle_keeper":
            return self._puzzle_runner, self._puzzle_runner_app_name
        return self._news_runner, self._news_runner_app_name

    def _resolve_tool_choice(self, item: UserMessageItem | None) -> str | None:
        """Extract tool choice from user message inference options."""
        if not item or not item.inference_options:
            return None
        tool_choice = item.inference_options.tool_choice
        if tool_choice and isinstance(tool_choice.id, str):
            return tool_choice.id
        return None
