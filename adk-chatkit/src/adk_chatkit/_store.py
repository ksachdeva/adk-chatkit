import logging
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
from google.adk.events import Event, EventActions
from google.adk.sessions import BaseSessionService
from google.adk.sessions.base_session_service import ListSessionsResponse

from ._client_tool_call import serialize_client_tool_call_item
from ._constants import CHATKIT_CLIENT_TOOL_CALLS_KEY, CHATKIT_THREAD_METADTA_KEY, CHATKIT_WIDGET_STATE_KEY
from ._context import ADKContext
from ._thread_utils import (
    get_thread_metadata_from_state,
    serialize_thread_metadata,
)
from ._widgets import serialize_widget_item

_LOGGER = logging.getLogger("adk_chatkit.store")


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
        _LOGGER.info(f"Loading thread {thread_id} for user {context.user_id} in app {context.app_name}")
        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=thread_id,
        )

        if not session:
            raise ValueError(
                f"Session with id {thread_id} not found for user {context.user_id} in app {context.app_name}"
            )

        return get_thread_metadata_from_state(session.state)

    async def save_thread(self, thread: ThreadMetadata, context: ADKContext) -> None:
        _LOGGER.info(f"Saving thread {thread.id} for user {context.user_id} in app {context.app_name}")
        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=thread.id,
        )

        if not session:
            session = await self._session_service.create_session(
                app_name=context.app_name,
                user_id=context.user_id,
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
        _LOGGER.info(
            f"Loading thread items for thread {thread_id} for user {context.user_id} in app {context.app_name}"
        )
        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=thread_id,
        )

        if not session:
            raise ValueError(
                f"Session with id {thread_id} not found for user {context.user_id} in app {context.app_name}"
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

                            # let's check for widget in the state that corresponds to this function call
                            widget_state = session.state.get(CHATKIT_WIDGET_STATE_KEY, {})
                            if fn_response.id in widget_state:
                                widget_data = widget_state[fn_response.id]
                                an_item = WidgetItem.model_validate(widget_data)

                            # let's check for adk-client-tool in the response
                            adk_client_tool = session.state.get(CHATKIT_CLIENT_TOOL_CALLS_KEY, {})
                            if fn_response.id in adk_client_tool:
                                client_tool_data = adk_client_tool[fn_response.id]
                                an_item = ClientToolCallItem.model_validate(client_tool_data)

            if an_item:
                thread_items.append(an_item)

        return Page(data=thread_items)

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: ADKContext) -> None:
        if not isinstance(item, (ClientToolCallItem, WidgetItem)):
            return

        _LOGGER.info(f"Adding thread item to thread {thread_id} for user {context.user_id} in app {context.app_name}")

        print(item)

        # the widget item is added in a function call so it's ID has the function call id
        # we issue a system event to add the widget item in the State keeping the info about which function call added it
        # so that it is able to be retrieved later and sequenced

        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=thread_id,
        )

        if not session:
            raise ValueError(
                f"Session with id {thread_id} not found for user {context.user_id} in app {context.app_name}"
            )

        if isinstance(item, ClientToolCallItem):
            state_delta = {
                CHATKIT_CLIENT_TOOL_CALLS_KEY: {item.id: serialize_client_tool_call_item(item)},
            }
        elif isinstance(item, WidgetItem):
            state_delta = {
                CHATKIT_WIDGET_STATE_KEY: {item.id: serialize_widget_item(item)},
            }

        actions_with_update = EventActions(state_delta=state_delta)
        system_event = Event(
            invocation_id=uuid4().hex,
            author="system",
            actions=actions_with_update,
            timestamp=datetime.now().timestamp(),
        )
        await self._session_service.append_event(session, system_event)

    async def save_attachment(self, attachment: Attachment, context: ADKContext) -> None:
        raise NotImplementedError()

    async def load_attachment(self, attachment_id: str, context: ADKContext) -> Attachment:
        raise NotImplementedError()

    async def delete_attachment(self, attachment_id: str, context: ADKContext) -> None:
        raise NotImplementedError()

    async def delete_thread_item(self, thread_id: str, item_id: str, context: ADKContext) -> None:
        _LOGGER.info(
            f"Deleting thread item {item_id} from thread {thread_id} for user {context.user_id} in app {context.app_name}"
        )
        # simply ignoring it for now (ClientToolCallItem is typically not deleted because of this)
        pass

    async def delete_thread(self, thread_id: str, context: ADKContext) -> None:
        _LOGGER.info(f"Deleting thread {thread_id} for user {context.user_id} in app {context.app_name}")
        await self._session_service.delete_session(
            app_name=context.app_name, user_id=context.user_id, session_id=thread_id
        )

    async def save_item(self, thread_id: str, item: ThreadItem, context: ADKContext) -> None:
        _LOGGER.info(
            f"Saving thread item {item.id} in thread {thread_id} for user {context.user_id} in app {context.app_name}"
        )
        if not isinstance(item, (ClientToolCallItem, WidgetItem)):
            return

        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=thread_id,
        )

        if not session:
            raise ValueError(
                f"Session with id {thread_id} not found for user {context.user_id} in app {context.app_name}"
            )

        if isinstance(item, ClientToolCallItem):
            state_delta = {
                CHATKIT_CLIENT_TOOL_CALLS_KEY: {item.id: serialize_client_tool_call_item(item)},
            }
        elif isinstance(item, WidgetItem):
            state_delta = {
                CHATKIT_WIDGET_STATE_KEY: {item.id: serialize_widget_item(item)},
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
        _LOGGER.info(
            f"Loading thread item {item_id} from thread {thread_id} for user {context.user_id} in app {context.app_name}"
        )
        session = await self._session_service.get_session(
            app_name=context.app_name,
            user_id=context.user_id,
            session_id=thread_id,
        )

        if not session:
            raise ValueError(
                f"Session with id {thread_id} not found for user {context.user_id} in app {context.app_name}"
            )

        # get the widget from the state
        widget_state = session.state.get(CHATKIT_WIDGET_STATE_KEY, {})
        if item_id in widget_state:
            widget_data = widget_state[item_id]
            widget_item = WidgetItem.model_validate(widget_data)
            return widget_item

        raise ValueError(f"Item with id {item_id} not found in thread {thread_id}")

    async def load_threads(
        self,
        limit: int,
        after: str | None,
        order: str,
        context: ADKContext,
    ) -> Page[ThreadMetadata]:
        _LOGGER.info(f"Loading threads for user {context.user_id} in app {context.app_name}")
        sessions_response: ListSessionsResponse = await self._session_service.list_sessions(
            app_name=context.app_name,
            user_id=context.user_id,
        )

        items: list[ThreadMetadata] = []

        for session in sessions_response.sessions:
            thread_metadata = get_thread_metadata_from_state(session.state)
            items.append(thread_metadata)

        return Page(data=items)
