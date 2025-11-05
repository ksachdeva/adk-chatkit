import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import datetime

from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageContentPartAdded,
    AssistantMessageContentPartDone,
    AssistantMessageContentPartTextDelta,
    AssistantMessageItem,
    ThreadItemAddedEvent,
    ThreadItemDoneEvent,
    ThreadItemUpdated,
    ThreadStreamEvent,
)
from google.adk.events import Event

from ._context import ADKAgentContext
from ._event_utils import AsyncQueueIterator, EventWrapper, merge_generators


async def stream_agent_response(
    context: ADKAgentContext,
    adk_response: AsyncGenerator[Event, None],
) -> AsyncIterator[ThreadStreamEvent]:
    queue_iterator = AsyncQueueIterator(context._events)
    response_id = str(uuid.uuid4())

    thread = context.thread

    content_index = 0
    async for event in merge_generators(adk_response, queue_iterator):
        if event is None:
            continue

        if isinstance(event, EventWrapper):
            yield event.event
            continue

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

    context._complete()

    # Drain remaining events
    async for event in queue_iterator:
        yield event.event

    # the last chatkit event is that of the client call
    if context.client_tool_call:
        yield ThreadItemDoneEvent(item=context.client_tool_call)
