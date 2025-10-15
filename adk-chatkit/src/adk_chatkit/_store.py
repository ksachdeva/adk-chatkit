from datetime import datetime

from chatkit.store import Store
from chatkit.types import Attachment, Page, ThreadItem, ThreadMetadata
from google.adk.sessions import BaseSessionService
from google.adk.sessions.base_session_service import ListSessionsResponse

from ._context import ADKContext


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

        return ThreadMetadata(
            id=session.id,
            title="No title",
            created_at=datetime.fromtimestamp(session.last_update_time),
            metadata={},
        )

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
            )

    async def load_thread_items(
        self,
        thread_id: str,
        after: str | None,
        limit: int,
        order: str,
        context: ADKContext,
    ) -> Page[ThreadItem]:
        return Page(data=[])

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
            # Convert session to thread item
            thread_metadata_item = ThreadMetadata(
                id=session.id,
                title="No title",
                created_at=datetime.fromtimestamp(session.last_update_time),
                metadata={},
            )
            items.append(thread_metadata_item)

        return Page(data=items)
