from __future__ import annotations

from adk_chatkit import stream_event, stream_widget
from chatkit.types import ClientEffectEvent
from google.adk.tools.tool_context import ToolContext

from ._state import AirlineAgentContext
from .widgets import (
    FlightSearchRequest,
    build_flight_options_widget,
    build_meal_preference_widget,
    generate_flight_options,
)


def _get_context(tool_context: ToolContext) -> AirlineAgentContext:
    """Get airline context from session state, creating if needed."""
    context = tool_context.state.get("context", None)
    if context is None:
        ctx = AirlineAgentContext.create_initial_context()
        tool_context.state["context"] = ctx.model_dump()
        return ctx
    return AirlineAgentContext.model_validate(context)


def _save_context(tool_context: ToolContext, ctx: AirlineAgentContext) -> None:
    """Save updated context back to session state."""
    tool_context.state["context"] = ctx.model_dump()


async def _sync_profile_effect(tool_context: ToolContext, ctx: AirlineAgentContext) -> None:
    """Send profile update effect to the client."""
    event = ClientEffectEvent(
        name="customer_profile/update",
        data={"profile": ctx.customer_profile.to_dict()},
    )
    await stream_event(event, tool_context)


def get_customer_profile(tool_context: ToolContext) -> str:
    """Retrieve the customer's profile.

    Returns:
        A string with the formatted customer profile.
    """
    ctx = _get_context(tool_context)
    return ctx.customer_profile.format()


async def change_seat(flight_number: str, seat: str, tool_context: ToolContext) -> dict[str, str]:
    """Move the passenger to a different seat on a flight.

    Args:
        flight_number: The flight number to change the seat on.
        seat: The new seat to assign to the passenger.

    Returns:
        A dictionary with a message confirming the seat change.
    """
    ctx = _get_context(tool_context)
    message = ctx.change_seat(flight_number, seat)
    _save_context(tool_context, ctx)
    await _sync_profile_effect(tool_context, ctx)
    return {"result": message}


async def cancel_trip(tool_context: ToolContext) -> dict[str, str]:
    """Cancel the traveller's upcoming trip and note the refund.

    Returns:
        A dictionary with a message confirming the cancellation.
    """
    ctx = _get_context(tool_context)
    message = ctx.cancel_trip()
    _save_context(tool_context, ctx)
    await _sync_profile_effect(tool_context, ctx)
    return {"result": message}


async def add_checked_bag(tool_context: ToolContext) -> dict[str, str | int]:
    """Add a checked bag to the reservation.

    Returns:
        A dictionary with a message confirming the addition and the total bags checked.
    """
    ctx = _get_context(tool_context)
    message = ctx.add_bag()
    _save_context(tool_context, ctx)
    await _sync_profile_effect(tool_context, ctx)
    return {"result": message, "bags_checked": ctx.customer_profile.bags_checked}


async def meal_preference_list(tool_context: ToolContext) -> dict[str, str]:
    """Display the meal preference picker widget.

    Returns:
        A dictionary with a message indicating the widget was shown.
    """
    widget = build_meal_preference_widget()
    await stream_widget(widget, tool_context)
    return {"result": "Shared meal preference options with the traveller."}


async def set_meal_preference(meal: str, tool_context: ToolContext) -> dict[str, str]:
    """Set the traveller's meal preference.

    Args:
        meal: The meal preference to set (e.g. vegetarian).
    Returns:
        A dictionary with a message confirming the meal preference update.
    """
    ctx = _get_context(tool_context)
    message = ctx.set_meal(meal)
    _save_context(tool_context, ctx)
    await _sync_profile_effect(tool_context, ctx)
    return {"result": message}


async def flight_option_list(
    destination: str,
    depart_date: str,
    return_date: str,
    cabin: str,
    tool_context: ToolContext,
    origin: str | None = None,
) -> dict[str, str]:
    """Share specific flight options after collecting destination, dates, and cabin.
    Returns:
        A dictionary with a message indicating the widget was shown.
    """
    ctx = _get_context(tool_context)

    origin_airport = (origin or "SFO").strip().upper()

    request = FlightSearchRequest(
        origin=origin_airport,
        destination=destination.strip().upper(),
        depart_date=depart_date.strip(),
        return_date=return_date.strip(),
        cabin=cabin.strip(),
    )

    ctx.customer_profile.log(
        f"Booking request for {origin_airport} → {destination.upper()} ({depart_date} to {return_date}).",
        kind="info",
    )
    _save_context(tool_context, ctx)

    options = generate_flight_options(request)
    widget = build_flight_options_widget(options, request)
    await stream_widget(widget, tool_context)

    return {"result": "Shared flight options with the traveller."}


async def request_assistance(note: str, tool_context: ToolContext) -> dict[str, str]:
    """Note a special assistance request for airport staff.

    Args:
        note: The assistance request details.
    Returns:
        A dictionary with a message confirming the assistance request.
    """
    ctx = _get_context(tool_context)
    message = ctx.request_assistance(note)
    _save_context(tool_context, ctx)
    await _sync_profile_effect(tool_context, ctx)
    return {"result": message}
