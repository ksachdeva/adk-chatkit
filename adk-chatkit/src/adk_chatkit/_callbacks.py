from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from ._constants import CLIENT_TOOL_KEY_IN_TOOL_RESPONSE, WIDGET_KEY_IN_TOOL_RESPONSE


def remove_widgets_and_client_tool_calls(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    for c in llm_request.contents:
        if c.parts is None:
            continue
        for p in c.parts:
            if not p.function_response:
                continue
            if p.function_response.response:
                p.function_response.response.pop(WIDGET_KEY_IN_TOOL_RESPONSE, None)
                p.function_response.response.pop(CLIENT_TOOL_KEY_IN_TOOL_RESPONSE, None)

    return None
