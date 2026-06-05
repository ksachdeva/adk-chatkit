from typing import Final

# NOTE: The string values here are used as keys in ADK session state and must
# not be changed without a migration strategy for existing sessions.
CHATKIT_THREAD_METADATA_KEY: Final[str] = "adk-chatkit-thread-metadata"
CHATKIT_WIDGET_STATE_KEY: Final[str] = "adk-chatkit-widget-state"
CHATKIT_CLIENT_TOOL_CALLS_KEY: Final[str] = "adk-chatkit-client-tool-calls"
