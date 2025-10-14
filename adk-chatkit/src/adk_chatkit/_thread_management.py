"""Session to Thread conversion utilities."""

import uuid
from datetime import datetime
from typing import Any, Literal

from chatkit.types import Page, Thread, ThreadItem, ThreadListParams, ThreadMetadata
from google.adk.sessions import BaseSessionService
from google.adk.sessions.base_session_service import ListSessionsResponse
from pydantic import BaseModel

from ._context import ADKContext

StoreItemType = Literal["thread", "message", "tool_call", "task", "workflow", "attachment"]


_ID_PREFIXES: dict[StoreItemType, str] = {
    "thread": "thr",
    "message": "msg",
    "tool_call": "tc",
    "workflow": "wf",
    "task": "tsk",
    "attachment": "atc",
}


def default_generate_id(item_type: StoreItemType) -> str:
    prefix = _ID_PREFIXES[item_type]
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def list_threads(
    adk_context: ADKContext,
    session_service: BaseSessionService,
    params: ThreadListParams,
) -> Page[ThreadMetadata]:
    """List threads for a given user."""

    sessions_response: ListSessionsResponse = await session_service.list_sessions(
        app_name=adk_context["app_name"],
        user_id=adk_context["user_id"],
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


async def load_thread(
    adk_context: ADKContext,
    session_id: str,
    session_service: BaseSessionService,
) -> ThreadMetadata:
    session = await session_service.get_session(
        app_name=adk_context["app_name"],
        user_id=adk_context["user_id"],
        session_id=session_id,
    )

    if not session:
        raise ValueError(
            f"Session with id {session_id} not found for user {adk_context['user_id']} in app {adk_context['app_name']}"
        )

    return ThreadMetadata(
        id=session.id,
        title="No title",
        created_at=datetime.fromtimestamp(session.last_update_time),
        metadata={},
    )


async def load_full_thread(
    adk_context: ADKContext,
    session_id: str,
    session_service: BaseSessionService,
) -> Thread:
    """Load full thread for a given user and session."""

    session = await session_service.get_session(
        app_name=adk_context["app_name"],
        user_id=adk_context["user_id"],
        session_id=session_id,
    )

    if not session:
        raise ValueError(
            f"Session with id {session_id} not found for user {adk_context['user_id']} in app {adk_context['app_name']}"
        )

    session_items: list[ThreadItem] = []
    # for ev in session.events:
    #     if ev.content and ev.content.parts and ev.content.parts[0].text:
    #         session_items.append(
    #             ThreadItem(
    #                 id=ev.invocation_id,
    #                 type="human" if ev.author == "user" else "ai",
    #                 created_at=datetime.fromtimestamp(ev.timestamp).isoformat(),
    #                 content=ev.content.parts[0].text,
    #             )
    #         )

    return Thread(
        title="No title",
        id=session.id,
        created_at=datetime.fromtimestamp(session.last_update_time),
        items=Page(data=session_items),
    )


async def create_thread(
    adk_context: ADKContext,
    session_service: BaseSessionService,
    state: dict[str, Any] | None = None,
) -> Thread:
    """Create a new thread for a given user."""

    thread_id = default_generate_id("thread")

    session = await session_service.create_session(
        app_name=adk_context["app_name"],
        user_id=adk_context["user_id"],
        session_id=thread_id,
        state=state,
    )

    return Thread(
        title="No title",
        id=session.id,
        created_at=datetime.fromtimestamp(session.last_update_time),
        items=Page(data=[]),
    )
