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
                    created_at=datetime.now(),
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
                        created_at=datetime.now(),
                    )
                )
