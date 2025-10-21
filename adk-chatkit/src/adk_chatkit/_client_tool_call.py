from typing import Any, Literal

from pydantic import BaseModel

from ._constants import CLIENT_TOOL_KEY_IN_TOOL_RESPONSE


class ClientToolCallState(BaseModel):
    """
    Returned from tool methods to indicate a client-side tool call.
    """

    name: str
    arguments: dict[str, Any]
    status: Literal["pending", "completed"] = "pending"


def add_client_tool_call_to_tool_response(
    response: dict[str, Any],
    client_tool_call: ClientToolCallState,
) -> None:
    """Add a client tool call to a tool response dictionary.

    Args:
        response: The tool response dictionary to modify.
        client_tool_call: The client tool call state to add.
    """
    response[CLIENT_TOOL_KEY_IN_TOOL_RESPONSE] = client_tool_call
