from collections.abc import AsyncGenerator, AsyncIterator
from datetime import datetime

from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageContentPartAdded,
    AssistantMessageContentPartDone,
    AssistantMessageContentPartTextDelta,
    AssistantMessageItem,
    ThreadItemAddedEvent,
    ThreadItemUpdated,
    ThreadMetadata,
    ThreadStreamEvent,
)
from google.adk.events import Event


async def stream_agent_response(
    thread: ThreadMetadata,
    adk_response: AsyncGenerator[Event, None],
) -> AsyncIterator[ThreadStreamEvent]:
    if adk_response is None:
        return

    content_index = 0
    async for event in adk_response:
        if event.content is None:
            # we need to throw item added event first
            yield ThreadItemAddedEvent(
                item=AssistantMessageItem(
                    id="__fake_id__",
                    content=[],
                    thread_id=thread.id,
                    created_at=datetime.now(),
                )
            )

            # and also yield an empty part added event
            yield ThreadItemUpdated(
                item_id="__fake_id__",
                update=AssistantMessageContentPartAdded(
                    content_index=content_index,
                    content=AssistantMessageContent(text=""),
                ),
            )
        else:
            if event.content.parts:
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

                        yield ThreadItemUpdated(item_id="__fake_id__", update=update)
