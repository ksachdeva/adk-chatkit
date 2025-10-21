import json
from typing import Any

from chatkit.types import ThreadMetadata


def serialize_thread_metadata(thread: ThreadMetadata) -> dict[str, Any]:
    json_dump = thread.model_dump_json(exclude_none=True, exclude={"items"})
    return json.loads(json_dump)  # type: ignore
