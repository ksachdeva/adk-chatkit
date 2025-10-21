import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import datetime

from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageContentPartAdded,
    AssistantMessageContentPartDone,
    AssistantMessageContentPartTextDelta,
    AssistantMessageItem,
    ClientToolCallItem,
    ThreadItemAddedEvent,
    ThreadItemDoneEvent,
    ThreadItemUpdated,
    ThreadMetadata,
    ThreadStreamEvent,
    WidgetItem,
)
from google.adk.events import Event

from ._client_tool_call import ClientToolCallState
from ._constants import CLIENT_TOOL_KEY_IN_TOOL_RESPONSE, WIDGET_KEY_IN_TOOL_RESPONSE


async def stream_agent_response(
    thread: ThreadMetadata,
    adk_response: AsyncGenerator[Event, None],
) -> AsyncIterator[ThreadStreamEvent]:
    if adk_response is None:
        return

    response_id = str(uuid.uuid4())

    content_index = 0
    async for event in adk_response:
        if event.content is None:
            # we need to throw item added event first
            yield ThreadItemAddedEvent(
                item=AssistantMessageItem(
                    id=response_id,
                    content=[],
                    thread_id=thread.id,
                    created_at=datetime.fromtimestamp(event.timestamp),
                )
            )

            # and also yield an empty part added event
            yield ThreadItemUpdated(
                item_id=response_id,
                update=AssistantMessageContentPartAdded(
                    content_index=content_index,
                    content=AssistantMessageContent(text=""),
                ),
            )
        else:
            # Since Widgets are recorded in the function responses
            # they are handled here
            if fn_responses := event.get_function_responses():
                for fn_response in fn_responses:
                    if not fn_response.response:
                        continue
                    widget = fn_response.response.get(WIDGET_KEY_IN_TOOL_RESPONSE, None)
                    if widget:
                        # No Streaming for Widgets for now
                        yield ThreadItemDoneEvent(
                            item=WidgetItem(
                                id=str(uuid.uuid4()),
                                thread_id=thread.id,
                                created_at=datetime.fromtimestamp(event.timestamp),
                                widget=widget,
                            )
                        )
                    adk_client_tool: ClientToolCallState | None = fn_response.response.get(
                        CLIENT_TOOL_KEY_IN_TOOL_RESPONSE, None
                    )
                    if adk_client_tool:
                        yield ThreadItemDoneEvent(
                            item=ClientToolCallItem(
                                id=event.id,
                                thread_id=thread.id,
                                name=adk_client_tool.name,
                                arguments=adk_client_tool.arguments,
                                status=adk_client_tool.status,
                                created_at=datetime.fromtimestamp(event.timestamp),
                                call_id=adk_client_tool.id,
                            ),
                        )

            if event.content.parts:
                text_from_final_update = ""
                for p in event.content.parts:
                    if p.text:
                        update: AssistantMessageContentPartTextDelta | AssistantMessageContentPartDone
                        if event.partial:
                            update = AssistantMessageContentPartTextDelta(
                                delta=p.text,
                                content_index=content_index,
                            )
                        else:
                            update = AssistantMessageContentPartDone(
                                content=AssistantMessageContent(text=p.text),
                                content_index=content_index,
                            )
                            text_from_final_update = p.text

                        yield ThreadItemUpdated(
                            item_id=response_id,
                            update=update,
                        )

                yield ThreadItemDoneEvent(
                    item=AssistantMessageItem(
                        id=response_id,
                        content=[AssistantMessageContent(text=text_from_final_update)],
                        thread_id=thread.id,
                        created_at=datetime.fromtimestamp(event.timestamp),
                    )
                )
