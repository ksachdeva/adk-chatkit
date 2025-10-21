import json
from typing import Any

from chatkit.types import ThreadMetadata
from google.adk.sessions.state import State

from ._constants import CHATKIT_THREAD_METADTA_KEY

_CLIENT_TOOL_PREFIX = "client-tool"


def serialize_thread_metadata(thread: ThreadMetadata) -> dict[str, Any]:
    json_dump = thread.model_dump_json(exclude_none=True, exclude={"items"})
    return json.loads(json_dump)  # type: ignore


def get_thread_metadata_from_state(state: State | dict[str, Any]) -> ThreadMetadata:
    thread_metadata_dict = state[CHATKIT_THREAD_METADTA_KEY]
    return ThreadMetadata.model_validate(thread_metadata_dict)


def add_client_tool_status(
    state: State | dict[str, Any],
    client_tool_id: str,
    status: str,
) -> ThreadMetadata:
    thread_metadata = get_thread_metadata_from_state(state)
    thread_metadata.metadata[f"{_CLIENT_TOOL_PREFIX}-{client_tool_id}"] = status
    return thread_metadata


def get_client_tool_status(
    state: State | dict[str, Any],
    client_tool_id: str,
) -> str | None:
    thread_metadata = get_thread_metadata_from_state(state)
    return thread_metadata.metadata.get(f"{_CLIENT_TOOL_PREFIX}-{client_tool_id}", None)
