from typing import Any

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Query
from google.adk.sessions.base_session_service import BaseSessionService
from pydantic import BaseModel

from backend._config import Settings
from backend.agents.airline import AirlineAgentContext

router = APIRouter(route_class=DishkaRoute)


class AgentRunRequest(BaseModel):
    app_name: str
    message: str
    session_id: str
    streaming: bool = False


class MessageResponse(BaseModel):
    content: str
    agent: str
    invocation_id: str


class AgentRunResponse(BaseModel):
    messages: list[MessageResponse]


@router.get("/health", summary="Check health of support agent")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/customer", summary="Customer Details")
async def customer_snapshot(
    session_service: FromDishka[BaseSessionService],
    settings: FromDishka[Settings],
    thread_id: str | None = Query(None, description="ChatKit thread identifier"),
) -> dict[str, Any]:
    # hard coded user id for now
    # as not doing an authentication
    user_id = "ksachdeva-1"

    if not thread_id:
        thread_id = "default-thread"

    session = await session_service.get_session(
        app_name=settings.AIRLINE_APP_NAME,
        user_id=user_id,
        session_id=thread_id,
    )

    if not session:
        airline_context = AirlineAgentContext.create_initial_context()
        session = await session_service.create_session(
            app_name=settings.AIRLINE_APP_NAME,
            user_id=user_id,
            session_id=thread_id,
            state={"context": airline_context.model_dump()},
        )

    context: dict[str, Any] | None = session.state.get("context", None)

    assert context is not None, "Context should be present in session state"

    return {"customer": context["customer_profile"]}
