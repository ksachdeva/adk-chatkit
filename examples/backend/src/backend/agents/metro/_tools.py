from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Final, List
from uuid import uuid4

from adk_chatkit import (
    ChatkitRunConfig,
    ClientToolCallState,
    issue_client_tool_call,
    stream_event,
    stream_widget,
)
from chatkit.types import (
    Annotation,
    AssistantMessageContent,
    AssistantMessageItem,
    ClientEffectEvent,
    EntitySource,
    ProgressUpdateEvent,
    ThreadItemDoneEvent,
)
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from ._context import MetroMapAgentContext
from .data.metro_map_store import Line, MetroMap, MetroMapStore, Station
from .widgets.line_select_widget import build_line_select_widget

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# TOOL RESPONSE MODELS


class MapResult(BaseModel):
    map: MetroMap


class LineListResult(BaseModel):
    lines: list[Line]


class StationListResult(BaseModel):
    stations: list[Station]


class LineDetailResult(BaseModel):
    line: Line
    stations: list[Station]


class StationDetailResult(BaseModel):
    station: Station
    lines: list[Line]


class SelectedStationsResult(BaseModel):
    station_ids: list[str]


# HELPER FUNCTIONS


async def _stream_client_effect(
    tool_context: ToolContext,
    name: str,
    data: dict[str, object],
) -> None:
    """Helper function to create and stream a ClientEffectEvent."""
    event = ClientEffectEvent(name=name, data=data)
    await stream_event(event, tool_context)


def _get_metro_store(tool_context: ToolContext) -> MetroMapStore:
    """Get the metro map store from the agent context."""
    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        context = run_config.context
        if isinstance(context, MetroMapAgentContext) and context.metro_map_store is not None:
            return context.metro_map_store

    # Fallback: Create a new store (shouldn't happen in normal operation)
    logger.warning("MetroMapStore not found in context, creating fallback store")
    data_dir = Path(__file__).parent / "data"
    return MetroMapStore(data_dir)


def _get_thread_id(tool_context: ToolContext) -> str:
    """Get the thread ID from the run config context."""
    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        thread_id: str = run_config.context.thread.id
        return thread_id
    return uuid4().hex


# TOOLS


async def show_line_selector(
    message: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Show a clickable widget listing metro lines.

    Args:
        message: Text shown above the widget to prompt the user.

    Returns:
        Confirmation that the widget was displayed.
    """
    logger.info("[TOOL CALL] show_line_selector")

    metro = _get_metro_store(tool_context)
    lines = metro.list_lines()
    widget = build_line_select_widget(lines)

    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        thread = run_config.context.thread

        # Stream the message first
        message_item = AssistantMessageItem(
            thread_id=thread.id,
            id=uuid4().hex,
            created_at=datetime.now(),
            content=[AssistantMessageContent(text=message)],
        )
        await stream_event(ThreadItemDoneEvent(item=message_item), tool_context)

    # Then stream the widget
    await stream_widget(widget, tool_context)

    return {"success": True, "result": "Line selector displayed", "lines": [line.id for line in lines]}


async def get_map(tool_context: ToolContext) -> dict[str, Any]:
    """Load the latest metro map with lines and stations. No parameters.

    Returns:
        The complete metro map data.
    """
    logger.info("[TOOL CALL] get_map")

    metro = _get_metro_store(tool_context)
    metro_map = metro.get_map()

    # Stream progress update
    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        await stream_event(ProgressUpdateEvent(text="Retrieving the latest metro map..."), tool_context)

    return {"map": metro_map.model_dump(mode="json")}


async def list_lines(tool_context: ToolContext) -> dict[str, Any]:
    """List all metro lines with their colors and endpoints. No parameters.

    Returns:
        List of all metro lines.
    """
    logger.info("[TOOL CALL] list_lines")

    metro = _get_metro_store(tool_context)
    lines = metro.list_lines()

    return {"lines": [line.model_dump(mode="json") for line in lines]}


async def list_stations(tool_context: ToolContext) -> dict[str, Any]:
    """List all stations and which lines serve them. No parameters.

    Returns:
        List of all stations.
    """
    logger.info("[TOOL CALL] list_stations")

    metro = _get_metro_store(tool_context)
    stations = metro.list_stations()

    return {"stations": [station.model_dump(mode="json") for station in stations]}


async def plan_route(
    route: List[dict[str, Any]],
    message: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Show the user the planned route.

    Args:
        route: Ordered list of stations in the journey. Each station should have id, name, and description.
        message: One-sentence description of the itinerary.

    Returns:
        Confirmation that the route was displayed.
    """
    logger.info("[TOOL CALL] plan_route %s", route)

    annotations: list[Annotation] = []
    for station_data in route:
        station_name = station_data.get("name", "")
        station_id = station_data.get("id", "")
        station_description = station_data.get("description", "")

        if station_name not in message:
            index = None
        else:
            index = message.index(station_name) + len(station_name)

        annotations.append(
            Annotation(
                source=EntitySource(
                    id=station_id,
                    icon="map-pin",
                    title=station_name,
                    description=station_description,
                    interactive=True,
                    label="Station",
                    data={"type": "station", "station_id": station_id, "name": station_name},
                ),
                index=index,
            )
        )

    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        thread = run_config.context.thread

        message_item = AssistantMessageItem(
            thread_id=thread.id,
            id=uuid4().hex,
            created_at=datetime.now(),
            content=[AssistantMessageContent(text=message, annotations=annotations)],
        )
        await stream_event(ThreadItemDoneEvent(item=message_item), tool_context)

    station_names = [s.get("name", "") for s in route]
    return {"success": True, "result": "Route displayed", "stations": station_names}


async def get_station(
    station_id: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Look up a single station and the lines serving it.

    Args:
        station_id: Station identifier to retrieve.

    Returns:
        Station details and lines serving it.
    """
    logger.info("[TOOL CALL] get_station %s", station_id)

    metro = _get_metro_store(tool_context)
    station = metro.find_station(station_id)

    if not station:
        raise ValueError(f"Station '{station_id}' was not found.")

    lines = [metro.find_line(line_id) for line_id in station.lines]
    valid_lines = [line for line in lines if line]

    return {
        "station": station.model_dump(mode="json"),
        "lines": [line.model_dump(mode="json") for line in valid_lines],
    }


async def add_station(
    station_name: str,
    line_id: str,
    tool_context: ToolContext,
    append: bool = True,
) -> dict[str, Any]:
    """Add a new station to the metro map.

    Args:
        station_name: The name of the station to add.
        line_id: The id of the line to add the station to.
        append: Whether to add the station to the end of the line (True) or the beginning (False). Defaults to True.

    Returns:
        The updated map data.
    """
    station_name = station_name.strip().title()
    logger.info("[TOOL CALL] add_station: %s to %s", station_name, line_id)

    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        await stream_event(ProgressUpdateEvent(text="Adding station..."), tool_context)

    try:
        metro = _get_metro_store(tool_context)
        updated_map, new_station = metro.add_station(station_name, line_id, append)

        # Stream client effect to update the map in the UI
        if isinstance(run_config, ChatkitRunConfig):
            await _stream_client_effect(
                tool_context,
                name="add_station",
                data={
                    "station_id": new_station.id,
                    "map": updated_map.model_dump(mode="json"),
                },
            )

        return {"map": updated_map.model_dump(mode="json")}

    except Exception as e:
        logger.error("[ERROR] add_station: %s", e)

        if isinstance(run_config, ChatkitRunConfig):
            thread = run_config.context.thread
            message_item = AssistantMessageItem(
                thread_id=thread.id,
                id=uuid4().hex,
                created_at=datetime.now(),
                content=[AssistantMessageContent(text=f"There was an error adding **{station_name}**")],
            )
            await stream_event(ThreadItemDoneEvent(item=message_item), tool_context)

        raise


async def get_selected_stations(tool_context: ToolContext) -> dict[str, Any]:
    """Fetch the ids of the currently selected stations from the client UI. No parameters.

    Returns:
        List of selected station IDs (will be empty until client responds).
    """
    logger.info("[TOOL CALL] get_selected_stations")

    # Stream progress update while waiting for client response
    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        await stream_event(
            ProgressUpdateEvent(text="Fetching selected stations from the map..."),
            tool_context,
        )

    # Issue client tool call to get selected stations from the frontend
    client_tool_call = ClientToolCallState(
        name="get_selected_stations",
        arguments={},
    )
    await issue_client_tool_call(client_tool_call, tool_context)

    return {"station_ids": [], "status": "pending_client_response"}


async def cite_stations_for_route(
    stations: List[dict[str, Any]],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Cite a list of stations for a route description.

    Args:
        stations: List of stations to cite. Each should have id, name, and description.

    Returns:
        Confirmation that stations were cited.
    """
    logger.info("[TOOL CALL] cite_stations_for_route %s", [s.get("name") for s in stations])

    # This tool is mainly for the agent to acknowledge it has cited stations
    # The actual citation happens through the plan_route annotations
    return {
        "success": True,
        "stations_cited": len(stations),
        "station_names": [s.get("name", "") for s in stations],
    }
