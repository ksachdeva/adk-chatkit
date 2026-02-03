from typing import Any

from adk_chatkit import ADKContext
from chatkit.server import StreamingResult
from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse
from starlette.responses import JSONResponse

from backend._config import Settings
from backend.agents.metro import MetroMap, MetroMapChatKitServer

router = APIRouter(route_class=DishkaRoute)


@router.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    settings: FromDishka[Settings],
    request_server: FromDishka[MetroMapChatKitServer],
) -> Response:
    payload = await request.body()
    print("Received metro-map payload:", payload)

    # Get map_id from header or default
    user_id = "metro-user-1"

    result = await request_server.process(
        payload,
        ADKContext(user_id=user_id, app_name=settings.METRO_MAP_APP_NAME),
    )

    print(result)

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


@router.get("/health", summary="Check health of metro-map agent")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/map", summary="Get the current metro map")
async def read_map(
    request_server: FromDishka[MetroMapChatKitServer],
) -> dict[str, Any]:
    return {"map": request_server.metro_map_store.dump_for_client()}


class MapUpdatePayload:
    map: MetroMap


@router.post("/map", summary="Update the metro map")
async def write_map(
    payload: dict[str, Any],
    request_server: FromDishka[MetroMapChatKitServer],
) -> dict[str, Any]:
    try:
        map_data = payload.get("map")
        if not map_data:
            raise ValueError("Missing 'map' in payload")
        metro_map = MetroMap.model_validate(map_data)
        request_server.metro_map_store.set_map(metro_map)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    return {"map": metro_map.model_dump(mode="json")}
