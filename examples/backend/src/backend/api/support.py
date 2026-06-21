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
from starlette.responses import JSONResponse

from backend._config import Settings
from backend.agents.airline import AirlineAgentContext, AirlineSupportChatKitServer

router = APIRouter(route_class=DishkaRoute)


@router.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    settings: FromDishka[Settings],
    request_server: FromDishka[AirlineSupportChatKitServer],
) -> Response:
    payload = await request.body()
    user_id = "ksachdeva-1"

    result = await request_server.process(
        payload,
        ADKContext(user_id=user_id, app_name=settings.AIRLINE_APP_NAME),
    )

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
    """Return customer profile for a given thread, or default if no thread."""
    user_id = "ksachdeva-1"

    if not thread_id:
        initial_context = AirlineAgentContext.create_initial_context()
        return {"customer": initial_context.customer_profile.to_dict()}

    session = await session_service.get_session(
        app_name=settings.AIRLINE_APP_NAME,
        user_id=user_id,
        session_id=thread_id,
    )

    if not session:
        initial_context = AirlineAgentContext.create_initial_context()
        return {"customer": initial_context.customer_profile.to_dict()}

    context_dict: dict[str, Any] | None = session.state.get("context", None)

    if context_dict is None:
        initial_context = AirlineAgentContext.create_initial_context()
        return {"customer": initial_context.customer_profile.to_dict()}

    ctx = AirlineAgentContext.model_validate(context_dict)
    return {"customer": ctx.customer_profile.to_dict()}
