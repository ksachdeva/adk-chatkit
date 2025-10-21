from typing import Any, Literal
from uuid import uuid4

from google.adk.tools import ToolContext
from pydantic import BaseModel, Field

from ._constants import CHATKIT_THREAD_METADTA_KEY, CLIENT_TOOL_KEY_IN_TOOL_RESPONSE
from ._thread_utils import (
    add_client_tool_status,
    serialize_thread_metadata,
)


class ClientToolCallState(BaseModel):
    """
    Returned from tool methods to indicate a client-side tool call.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)

    name: str
    arguments: dict[str, Any]
    status: Literal["pending", "completed"] = "pending"


def add_client_tool_call_to_tool_response(
    response: dict[str, Any],
    client_tool_call: ClientToolCallState,
    tool_context: ToolContext,
) -> None:
    """Add a client tool call to a tool response dictionary.

    Args:
        response: The tool response dictionary to modify.
        client_tool_call: The client tool call state to add.
    """

    thread_metadata = add_client_tool_status(
        tool_context.state,
        client_tool_call.id,
        client_tool_call.status,
    )

    # update the state
    tool_context.state[CHATKIT_THREAD_METADTA_KEY] = serialize_thread_metadata(thread_metadata)

    response[CLIENT_TOOL_KEY_IN_TOOL_RESPONSE] = client_tool_call
