from datetime import datetime
from uuid import uuid4

from chatkit.store import Store
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    Attachment,
    ClientToolCallItem,
    InferenceOptions,
    Page,
    ThreadItem,
    ThreadMetadata,
    UserMessageContent,
    UserMessageItem,
    UserMessageTextContent,
    WidgetItem,
)
from chatkit.widgets import Card
from google.adk.events import Event, EventActions
from google.adk.sessions import BaseSessionService
from google.adk.sessions.base_session_service import ListSessionsResponse

from ._client_tool_call import ClientToolCallState
from ._constants import CHATKIT_THREAD_METADTA_KEY, CLIENT_TOOL_KEY_IN_TOOL_RESPONSE, WIDGET_KEY_IN_TOOL_RESPONSE
from ._context import ADKContext
from ._thread_utils import (
    add_client_tool_status,
    get_client_tool_status,
    get_thread_metadata_from_state,
    serialize_thread_metadata,
)


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

        return get_thread_metadata_from_state(session.state)

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
                state={CHATKIT_THREAD_METADTA_KEY: serialize_thread_metadata(thread)},
            )
        else:
            state_delta = {
                CHATKIT_THREAD_METADTA_KEY: serialize_thread_metadata(thread),
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
                # we should only send the message if it has content
                # that is not function calls or response
                text_message_content = _to_assistant_message_content(event)

                if text_message_content:
                    an_item = AssistantMessageItem(
                        id=event.id,
                        thread_id=thread_id,
                        created_at=datetime.fromtimestamp(event.timestamp),
                        content=text_message_content,
                    )
                else:
                    # let's see if this a function call response
                    # with a widget. If yes, then we will tranmist WidgetItem
                    if fn_responses := event.get_function_responses():
                        for fn_response in fn_responses:
                            if not fn_response.response:
                                continue
                            # let's check for widget in the response
                            widget = fn_response.response.get(WIDGET_KEY_IN_TOOL_RESPONSE, None)
                            if widget:
                                an_item = WidgetItem(
                                    id=event.id,
                                    thread_id=thread_id,
                                    created_at=datetime.fromtimestamp(event.timestamp),
                                    widget=Card.model_validate(widget),
                                )
                            # let's check for adk-client-tool in the response
                            adk_client_tool = fn_response.response.get(CLIENT_TOOL_KEY_IN_TOOL_RESPONSE, None)
                            if adk_client_tool:
                                adk_client_tool = ClientToolCallState.model_validate(adk_client_tool)
                                status = get_client_tool_status(
                                    session.state,
                                    adk_client_tool.id,
                                )
                                if status:
                                    an_item = ClientToolCallItem(
                                        id=event.id,
                                        thread_id=thread_id,
                                        name=adk_client_tool.name,
                                        arguments=adk_client_tool.arguments,
                                        status=status,  # type: ignore
                                        created_at=datetime.fromtimestamp(event.timestamp),
                                        call_id=adk_client_tool.id,
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
        # simply ignoring it for now (ClientToolCallItem is typically not deleted because of this)
        pass

    async def delete_thread(self, thread_id: str, context: ADKContext) -> None:
        raise NotImplementedError()

    async def save_item(self, thread_id: str, item: ThreadItem, context: ADKContext) -> None:
        # we will only handle specify types of items here
        # as quite many are automatically handled by runner
        if isinstance(item, ClientToolCallItem):
            session = await self._session_service.get_session(
                app_name=context["app_name"],
                user_id=context["user_id"],
                session_id=thread_id,
            )

            if not session:
                raise ValueError(
                    f"Session with id {thread_id} not found for user {context['user_id']} in app {context['app_name']}"
                )

            thread_metadata = add_client_tool_status(session.state, item.call_id, item.status)

            state_delta = {
                CHATKIT_THREAD_METADTA_KEY: serialize_thread_metadata(thread_metadata),
            }

            actions_with_update = EventActions(state_delta=state_delta)
            system_event = Event(
                invocation_id=uuid4().hex,
                author="system",
                actions=actions_with_update,
                timestamp=datetime.now().timestamp(),
            )
            await self._session_service.append_event(session, system_event)

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
            thread_metadata = get_thread_metadata_from_state(session.state)
            items.append(thread_metadata)

        return Page(data=items)
