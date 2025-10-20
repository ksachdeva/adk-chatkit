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
from backend.agents.facts import FactContext, FactsChatkitServer

router = APIRouter(route_class=DishkaRoute)


@router.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    settings: FromDishka[Settings],
    request_server: FromDishka[FactsChatkitServer],
) -> Response:
    payload = await request.body()
    print("Received payload:", payload)

    user_id = "ksachdeva-1"

    result = await request_server.process(
        payload,
        ADKContext(user_id=user_id, app_name=settings.FACTS_APP_NAME),
    )

    print(result)

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


@router.get("/health", summary="Check health of facts agent")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
