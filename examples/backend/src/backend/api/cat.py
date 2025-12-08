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
from backend.agents.cat import CatAgentContext, CatChatkitServer, CatState

router = APIRouter(route_class=DishkaRoute)


@router.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    settings: FromDishka[Settings],
    request_server: FromDishka[CatChatkitServer],
) -> Response:
    payload = await request.body()
    print("Received payload:", payload)

    user_id = "ksachdeva-1"

    result = await request_server.process(
        payload,
        ADKContext(user_id=user_id, app_name=settings.CAT_APP_NAME),
    )

    print(result)

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


@router.get("/health", summary="Check health of cat agent")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/cat", summary="Cat Details")
async def cat_snapshot(
    session_service: FromDishka[BaseSessionService],
    settings: FromDishka[Settings],
    thread_id: str | None = Query(None, description="ChatKit thread identifier"),
) -> dict[str, Any]:
    user_id = "ksachdeva-1"

    if not thread_id:
        context = CatAgentContext.create_initial_context().model_dump()
        state = CatState.from_dict(context["cat_state"])
        return {"cat": state.to_payload()}

    session = await session_service.get_session(
        app_name=settings.CAT_APP_NAME,
        user_id=user_id,
        session_id=thread_id,
    )

    if not session:
        raise ValueError(f"Session with id {thread_id} not found")

    context: dict[str, Any] | None = session.state.get("context", None)

    if context is None:
        raise ValueError(f"No context found in session {thread_id}")

    cat_context = CatAgentContext.model_validate(context)
    state = CatState.from_dict(cat_context.cat_state)
    return {"cat": state.to_payload(thread_id)}
