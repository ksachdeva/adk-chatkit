import json
from typing import Any, Final

from chatkit.types import ThreadMetadata

STATE_CHATKIT_THREAD_METADTA_KEY: Final[str] = "chatkit-thread-metadata"


def serialize_thread_metadata(thread: ThreadMetadata) -> dict[str, Any]:
    json_dump = thread.model_dump_json(exclude_none=True, exclude={"items"})
    return json.loads(json_dump)  # type: ignore
