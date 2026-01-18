import re
from collections.abc import AsyncIterator
from itertools import chain
from pathlib import Path
from typing import Any, Iterable, cast

from adk_chatkit import ADKAgentContext, ADKContext, ADKStore, stream_agent_response
from chatkit.server import ChatKitServer
from chatkit.types import (
    Annotation,
    AssistantMessageContent,
    AssistantMessageItem,
    ClientToolCallItem,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types
from langchain_core.vectorstores import VectorStore

from backend._config import Settings
from backend._runner_manager import RunnerManager

from ._agent import KnowledgeAgent
from ._documents import (
    DOCUMENTS_BY_FILENAME,
    DOCUMENTS_BY_SLUG,
    DOCUMENTS_BY_STEM,
    DocumentMetadata,
)
from ._tools import Searcher

_FILENAME_REGEX = re.compile(r"(0[1-8]_[a-z0-9_\-]+\.(?:pdf|html))", re.IGNORECASE)


def _normalise_filename(value: str) -> str:
    return Path(value).name.strip().lower()


def _slug(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _make_knowledge_agent(settings: Settings, searcher: Searcher) -> KnowledgeAgent:
    return KnowledgeAgent(
        llm=LiteLlm(
            model=settings.gpt41_agent.llm.model_name,
            **settings.gpt41_agent.llm.provider_args,
        ),
        tools=[
            searcher.file_search,
        ],
        generate_content_config=settings.gpt41_agent.generate_content,
    )


def _user_message_text(item: UserMessageItem) -> str:
    parts: list[str] = []
    for part in item.content:
        text = getattr(part, "text", None)
        if text:
            parts.append(text)
    return " ".join(parts).strip()


def _is_tool_completion_item(item: Any) -> bool:
    return isinstance(item, ClientToolCallItem)


def _resolve_document(annotation: Annotation) -> DocumentMetadata | None:
    source = getattr(annotation, "source", None)
    if not source or getattr(source, "type", None) != "file":
        return None

    filename = getattr(source, "filename", None)
    if filename:
        normalised = _normalise_filename(filename)
        match = DOCUMENTS_BY_FILENAME.get(normalised)
        if match:
            return match
        stem_match = DOCUMENTS_BY_STEM.get(Path(normalised).stem.lower())
        if stem_match:
            return stem_match
        slug_match = DOCUMENTS_BY_SLUG.get(_slug(normalised))
        if slug_match:
            return slug_match

    title = getattr(source, "title", None)
    if title:
        candidate = DOCUMENTS_BY_SLUG.get(_slug(title))
        if candidate:
            return candidate

    description = getattr(source, "description", None)
    if description:
        candidate = DOCUMENTS_BY_SLUG.get(_slug(description))
        if candidate:
            return candidate

    return None


def _documents_from_text(text: str) -> Iterable[DocumentMetadata]:
    if not text:
        return []
    matches = {match.lower() for match in _FILENAME_REGEX.findall(text)}
    if not matches:
        return []
    results: list[DocumentMetadata] = []
    for filename in matches:
        doc = DOCUMENTS_BY_FILENAME.get(filename)
        if doc and doc not in results:
            results.append(doc)
    return results


def _extract_citations(item: AssistantMessageItem) -> Iterable[dict[str, Any]]:
    found = False
    for content in item.content:
        if not isinstance(content, AssistantMessageContent):
            continue
        for annotation in content.annotations:
            document = _resolve_document(annotation)
            if not document:
                continue
            found = True
            yield {
                "document_id": document.id,
                "filename": document.filename,
                "title": document.title,
                "description": document.description,
                "annotation_index": annotation.index,
            }
    if not found:
        texts = chain.from_iterable(
            content.text.splitlines() for content in item.content if isinstance(content, AssistantMessageContent)
        )
        for line in texts:
            for document in _documents_from_text(line):
                yield {
                    "document_id": document.id,
                    "filename": document.filename,
                    "title": document.title,
                    "description": document.description,
                    "annotation_index": None,
                }


class KnowledgeAssistantChatkitServer(ChatKitServer[ADKContext]):
    def __init__(
        self,
        store: ADKStore,
        runner_manager: RunnerManager,
        settings: Settings,
        vector_store: VectorStore,
    ) -> None:
        super().__init__(store)
        self._vector_store = vector_store
        searcher = Searcher(vector_store=self._vector_store)
        agent = _make_knowledge_agent(settings, searcher)
        self._store = store
        self._runner = runner_manager.add_runner(settings.KNOWLEDGE_APP_NAME, agent)

    async def latest_citations(
        self,
        thread_id: str,
        context: ADKContext,
    ) -> list[dict[str, Any]]:
        # Implement the logic to fetch the latest citations
        items = await self.store.load_thread_items(
            thread_id,
            after=None,
            limit=50,
            order="desc",
            context=context,
        )

        for item in items.data:
            if isinstance(item, AssistantMessageItem):
                citations = list(_extract_citations(item))
                if citations:
                    return citations
        return []

    async def respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        if item is None:
            return

        if _is_tool_completion_item(item):
            return

        message_text = _user_message_text(item)
        if not message_text:
            return

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=message_text)],
        )

        agent_context = ADKAgentContext(
            app_name=context.app_name,
            user_id=context.user_id,
            thread=thread,
        )

        event_stream = self._runner.run_async(
            user_id=context.user_id,
            session_id=thread.id,
            new_message=content,
            run_config=RunConfig(streaming_mode=StreamingMode.NONE),
        )

        async for event in stream_agent_response(agent_context, event_stream):
            yield event

        # update session service for any pending items here
        adk_store = cast(ADKStore, self.store)
        await adk_store.issue_system_event_updates(thread_id=thread.id, context=context)
