from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import cast

from chatkit.server import ChatKitServer
from chatkit.types import (
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)

from ._context import ADKContext
from ._store import ADKStore


class ADKChatKitServer(ChatKitServer[ADKContext]):
    def __init__(
        self,
        store: ADKStore,
    ) -> None:
        super().__init__(store)

    @abstractmethod
    def _adk_respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        raise NotImplementedError("This method should be implemented by subclasses of ADKChatKitServer")

    async def respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: ADKContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        async for event in self._adk_respond(thread, item, context):
            yield event

        # update session service for any pending items here
        adk_store = cast(ADKStore, self.store)
        await adk_store.issue_system_event_updates(thread_id=thread.id, context=context)
