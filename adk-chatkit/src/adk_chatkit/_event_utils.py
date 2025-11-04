import asyncio
from collections.abc import AsyncIterator
from typing import TypeVar

from chatkit.types import ThreadStreamEvent

T1 = TypeVar("T1")
T2 = TypeVar("T2")


class QueueCompleteSentinel: ...


async def merge_generators(
    a: AsyncIterator[T1],
    b: AsyncIterator[T2],
) -> AsyncIterator[T1 | T2]:
    pending: list[AsyncIterator[T1 | T2]] = [a, b]
    pending_tasks: dict[asyncio.Task, AsyncIterator[T1 | T2]] = {
        asyncio.ensure_future(g.__anext__()): g for g in pending
    }
    while len(pending_tasks) > 0:
        done, _ = await asyncio.wait(pending_tasks.keys(), return_when="FIRST_COMPLETED")
        stop = False
        for d in done:
            try:
                result = d.result()
                yield result
                dg = pending_tasks[d]
                pending_tasks[asyncio.ensure_future(dg.__anext__())] = dg
            except StopAsyncIteration:
                stop = True
            finally:
                del pending_tasks[d]
        if stop:
            for task in pending_tasks.keys():
                if not task.cancel():
                    try:
                        yield task.result()
                    except asyncio.CancelledError:
                        pass
                    except asyncio.InvalidStateError:
                        pass
            break


class EventWrapper:
    def __init__(self, event: ThreadStreamEvent):
        self.event = event


class AsyncQueueIterator(AsyncIterator[EventWrapper]):
    def __init__(self, queue: asyncio.Queue[ThreadStreamEvent | QueueCompleteSentinel]):
        self.queue = queue
        self.completed = False

    def __aiter__(self) -> AsyncIterator[EventWrapper]:
        return self

    async def __anext__(self) -> EventWrapper:
        if self.completed:
            raise StopAsyncIteration

        item = await self.queue.get()
        if isinstance(item, QueueCompleteSentinel):
            self.completed = True
            raise StopAsyncIteration
        return EventWrapper(item)

    def drain_and_complete(self) -> None:
        """Empty the underlying queue without awaiting and mark this iterator completed.

        This is intended for cleanup paths where we must guarantee no awaits
        occur. All queued items, including any completion sentinel, are
        discarded.
        """
        while True:
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self.completed = True
