import json
from datetime import datetime
from typing import Any, Final
from uuid import uuid4

from chatkit.store import Store
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    Attachment,
    InferenceOptions,
    Page,
    ThreadItem,
    ThreadMetadata,
    UserMessageContent,
    UserMessageItem,
    UserMessageTextContent,
)
from google.adk.events import Event, EventActions
from google.adk.sessions import BaseSessionService
from google.adk.sessions.base_session_service import ListSessionsResponse

from ._context import ADKContext

_CHATKIT_THREAD_METADTA: Final[str] = "chatkit-thread-metadata"


def _to_user_message_content(event: Event) -> list[UserMessageContent]:
    if not event.content or not event.content.parts:
        return []

    contents: list[UserMessageContent] = []
    for part in event.content.parts:
        if part.text:
            contents.append(UserMessageTextContent(text=part.text))

    return contents


def _to_assistant_message_content(event: Event) -> list[AssistantMessageContent]:
    if not event.content or not event.content.parts:
        return []

    contents: list[AssistantMessageContent] = []
    for part in event.content.parts:
        if part.text:
            contents.append(AssistantMessageContent(text=part.text))

    return contents


def _serialize_thread_metadata(thread: ThreadMetadata) -> dict[str, Any]:
    json_dump = thread.model_dump_json(exclude_none=True, exclude={"items"})
    return json.loads(json_dump)  # type: ignore


class ADKStore(Store[ADKContext]):
    def __init__(self, session_service: BaseSessionService) -> None:
        self._session_service = session_service

    async def load_thread(self, thread_id: str, context: ADKContext) -> ThreadMetadata:
        session = await self._session_service.get_session(
            app_name=context["app_name"],
            user_id=context["user_id"],
            session_id=thread_id,
        )

        if not session:
            raise ValueError(
                f"Session with id {thread_id} not found for user {context['user_id']} in app {context['app_name']}"
            )

        return ThreadMetadata.model_validate(session.state[_CHATKIT_THREAD_METADTA])

    async def save_thread(self, thread: ThreadMetadata, context: ADKContext) -> None:
        session = await self._session_service.get_session(
            app_name=context["app_name"],
            user_id=context["user_id"],
            session_id=thread.id,
        )

        if not session:
            session = await self._session_service.create_session(
                app_name=context["app_name"],
                user_id=context["user_id"],
                session_id=thread.id,
                state={_CHATKIT_THREAD_METADTA: _serialize_thread_metadata(thread)},
            )
        else:
            state_delta = {
                _CHATKIT_THREAD_METADTA: _serialize_thread_metadata(thread),
            }
            actions_with_update = EventActions(state_delta=state_delta)
            system_event = Event(
                invocation_id=uuid4().hex,
                author="system",
                actions=actions_with_update,
                timestamp=datetime.now().timestamp(),
            )
            await self._session_service.append_event(session, system_event)

    async def load_thread_items(
        self,
        thread_id: str,
        after: str | None,
        limit: int,
        order: str,
        context: ADKContext,
    ) -> Page[ThreadItem]:
        session = await self._session_service.get_session(
            app_name=context["app_name"],
            user_id=context["user_id"],
            session_id=thread_id,
        )

        if not session:
            raise ValueError(
                f"Session with id {thread_id} not found for user {context['user_id']} in app {context['app_name']}"
            )

        thread_items: list[ThreadItem] = []
        for event in session.events:
            an_item: ThreadItem | None = None
            if event.author == "user":
                an_item = UserMessageItem(
                    id=event.id,
                    thread_id=thread_id,
                    created_at=datetime.fromtimestamp(event.timestamp),
                    content=_to_user_message_content(event),
                    attachments=[],
                    inference_options=InferenceOptions(),
                )
            else:
                an_item = AssistantMessageItem(
                    id=event.id,
                    thread_id=thread_id,
                    created_at=datetime.fromtimestamp(event.timestamp),
                    content=_to_assistant_message_content(event),
                )

            if an_item:
                thread_items.append(an_item)

        return Page(data=thread_items)

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: ADKContext) -> None:
        # items are added to the session by runner
        pass

    async def save_attachment(self, attachment: Attachment, context: ADKContext) -> None:
        raise NotImplementedError()

    async def load_attachment(self, attachment_id: str, context: ADKContext) -> Attachment:
        raise NotImplementedError()

    async def delete_attachment(self, attachment_id: str, context: ADKContext) -> None:
        raise NotImplementedError()

    async def delete_thread_item(self, thread_id: str, item_id: str, context: ADKContext) -> None:
        raise NotImplementedError()

    async def delete_thread(self, thread_id: str, context: ADKContext) -> None:
        raise NotImplementedError()

    async def save_item(self, thread_id: str, item: ThreadItem, context: ADKContext) -> None:
        raise NotImplementedError()

    async def load_item(self, thread_id: str, item_id: str, context: ADKContext) -> ThreadItem:
        raise NotImplementedError()

    async def load_threads(
        self,
        limit: int,
        after: str | None,
        order: str,
        context: ADKContext,
    ) -> Page[ThreadMetadata]:
        sessions_response: ListSessionsResponse = await self._session_service.list_sessions(
            app_name=context["app_name"],
            user_id=context["user_id"],
        )

        items: list[ThreadMetadata] = []

        for session in sessions_response.sessions:
            thread_metatdata_item = ThreadMetadata.model_validate(session.state[_CHATKIT_THREAD_METADTA])
            items.append(thread_metatdata_item)

        return Page(data=items)
