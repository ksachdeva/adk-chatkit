from typing import Any, Literal

from pydantic import BaseModel


class ClientToolCallState(BaseModel):
    """
    Returned from tool methods to indicate a client-side tool call.
    """

    name: str
    arguments: dict[str, Any]
    status: Literal["pending", "completed"] = "pending"
