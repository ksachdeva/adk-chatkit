from typing import Any

from google.adk.events import Event
from google.adk.sessions import Session
from google.adk.sessions.database_session_service import DatabaseSessionService


class RefreshedSessionService(DatabaseSessionService):
    def __init__(self, db_url: str, **kwargs: Any) -> None:
        super().__init__(db_url, **kwargs)

    async def append_event(self, session: Session, event: Event) -> Event:
        """Append event with session refresh to prevent stale session errors."""
        # Refresh the session before appending to get the latest state
        refreshed_session = await self.get_session(
            app_name=session.app_name, user_id=session.user_id, session_id=session.id
        )

        if refreshed_session:
            session.last_update_time = refreshed_session.last_update_time
            session.events = refreshed_session.events
            session.state = refreshed_session.state

        # Use the refreshed session for the append operation
        return await super().append_event(session, event)
