from typing import Any

from adk_chatkit import ADKContext
from chatkit.server import StreamingResult
from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response, StreamingResponse
from google.adk.sessions.base_session_service import BaseSessionService
from pydantic import BaseModel
from starlette.responses import JSONResponse

from backend._config import Settings
from backend._runner_manager import RunnerManager
from backend.agents.airline import AirlineAgentContext, AirlineSupportChatkitServer

router = APIRouter(route_class=DishkaRoute)


@router.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    settings: FromDishka[Settings],
    runner_manager: FromDishka[RunnerManager],
    request_server: FromDishka[AirlineSupportChatkitServer],
) -> Response:
    payload = await request.body()
    print("Received payload:", payload)

    user_id = "ksachdeva-1"

    result = await request_server.process(
        payload,
        ADKContext(user_id=user_id, app_name=settings.AIRLINE_APP_NAME),
    )

    print(result)

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


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

    if context is None:
        context = AirlineAgentContext.create_initial_context().model_dump()
        session.state["context"] = context

    return {"customer": context["customer_profile"]}
