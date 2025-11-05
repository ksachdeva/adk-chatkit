import json
from typing import Any, Literal
from uuid import uuid4

from chatkit.types import ClientToolCallItem
from pydantic import BaseModel, Field


class ClientToolCallState(BaseModel):
    """
    Returned from tool methods to indicate a client-side tool call.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)

    name: str
    arguments: dict[str, Any]
    status: Literal["pending", "completed"] = "pending"


def serialize_client_tool_call_item(client_tool_call: ClientToolCallItem) -> dict[str, Any]:
    json_dump = client_tool_call.model_dump_json(exclude_none=True)
    return json.loads(json_dump)  # type: ignore
