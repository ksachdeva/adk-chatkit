import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import AsyncGenerator, AsyncIterable, Callable, assert_never

from chatkit.types import (
    ChatKitReq,
    NonStreamingReq,
    Page,
    StreamingReq,
    ThreadCreatedEvent,
    ThreadItemDoneEvent,
    ThreadMetadata,
    ThreadsAddUserMessageReq,
    ThreadsCreateReq,
    ThreadsGetByIdReq,
    ThreadsListReq,
    ThreadStreamEvent,
    UserMessageInput,
    UserMessageItem,
    is_streaming_req,
)
from google.adk.sessions import BaseSessionService
from pydantic import BaseModel, TypeAdapter

from ._context import ADKContext
from ._thread_management import create_thread, default_generate_id, list_threads, load_full_thread, load_thread

DEFAULT_PAGE_SIZE = 20


class StreamingResult(AsyncIterable[bytes]):
    def __init__(self, stream: AsyncGenerator[bytes, None]):
        self.json_events = stream

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        async for event in self.json_events:
            yield event


class NonStreamingResult:
    def __init__(self, result: bytes):
        self.json = result


def _serialize(obj: BaseModel) -> bytes:
    return obj.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")


class ADKRequestProcessor(ABC):
    def __init__(self, session_service: BaseSessionService) -> None:
        self._session_service = session_service

    @abstractmethod
    async def respond(
        self,
        adk_context: ADKContext,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
    ) -> AsyncIterator[ThreadStreamEvent]:
        pass

    async def process(
        self,
        request: str | bytes | bytearray,
        adk_context: ADKContext,
    ) -> StreamingResult | NonStreamingResult:
        parsed_request = TypeAdapter[ChatKitReq](ChatKitReq).validate_json(request)
        if is_streaming_req(parsed_request):
            return StreamingResult(self._process_streaming(parsed_request, adk_context))
        non_stream_result = await self._process_non_streaming(parsed_request, adk_context)
        return NonStreamingResult(non_stream_result)

    def _build_user_message_item(
        self,
        input: UserMessageInput,
        thread: ThreadMetadata,
    ) -> UserMessageItem:
        return UserMessageItem(
            id=default_generate_id("message"),
            content=input.content,
            thread_id=thread.id,
            attachments=[],
            quoted_text=input.quoted_text,
            inference_options=input.inference_options,
            created_at=datetime.now(),
        )

    async def _process_new_thread_item_respond(
        self,
        adk_context: ADKContext,
        thread: ThreadMetadata,
        item: UserMessageItem,
    ) -> AsyncIterator[ThreadStreamEvent]:
        yield ThreadItemDoneEvent(item=item)

        stream = self.respond(adk_context, thread, item)

        async for event in stream:
            yield event

    async def _process_streaming(
        self,
        request: StreamingReq,
        adk_context: ADKContext,
    ) -> AsyncGenerator[bytes, None]:
        async for event in self._process_streaming_impl(request, adk_context):
            b = _serialize(event)
            yield b"data: " + b + b"\n\n"

    async def _process_streaming_impl(
        self,
        request: StreamingReq,
        adk_context: ADKContext,
    ) -> AsyncGenerator[ThreadStreamEvent, None]:
        match request:
            case ThreadsCreateReq():
                thread = await create_thread(
                    adk_context=adk_context,
                    session_service=self._session_service,
                )
                yield ThreadCreatedEvent(thread=thread)
                user_message = self._build_user_message_item(request.params.input, thread)
                async for event in self._process_new_thread_item_respond(
                    adk_context,
                    thread,
                    user_message,
                ):
                    yield event

            case ThreadsAddUserMessageReq():
                thread_metadata = await load_thread(
                    adk_context=adk_context,
                    session_id=request.params.thread_id,
                    session_service=self._session_service,
                )
                user_message = self._build_user_message_item(request.params.input, thread_metadata)
                async for event in self._process_new_thread_item_respond(
                    adk_context,
                    thread_metadata,
                    user_message,
                ):
                    yield event

            case _:
                assert_never(request)

    async def _process_non_streaming(
        self,
        request: NonStreamingReq,
        adk_context: ADKContext,
    ) -> bytes:
        match request:
            case ThreadsListReq():
                params = request.params
                page = await list_threads(
                    adk_context=adk_context,
                    session_service=self._session_service,
                    params=params,
                )
                return _serialize(page)

            case ThreadsGetByIdReq():
                thread = await load_full_thread(
                    adk_context=adk_context,
                    session_id=request.params.thread_id,
                    session_service=self._session_service,
                )
                return _serialize(thread)
            case _:
                assert_never(request)
