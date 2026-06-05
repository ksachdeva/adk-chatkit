import json
from typing import Any

from chatkit.types import ThreadMetadata
from google.adk.sessions.state import State

from ._constants import CHATKIT_THREAD_METADATA_KEY


def serialize_thread_metadata(thread: ThreadMetadata) -> dict[str, Any]:
    json_dump = thread.model_dump_json(exclude_none=True, exclude={"items"})
    return json.loads(json_dump)  # type: ignore


def get_thread_metadata_from_state(state: State | dict[str, Any]) -> ThreadMetadata:
    """Deserialize ThreadMetadata from ADK session state.

    Raises:
        KeyError: If the session state does not contain chatkit metadata. This
            typically means the session was created outside of adk-chatkit.
    """
    thread_metadata_dict = state.get(CHATKIT_THREAD_METADATA_KEY)
    if thread_metadata_dict is None:
        raise KeyError(
            f"Session state is missing the '{CHATKIT_THREAD_METADATA_KEY}' key. "
            "This session may not have been created by adk-chatkit."
        )
    return ThreadMetadata.model_validate(thread_metadata_dict)
