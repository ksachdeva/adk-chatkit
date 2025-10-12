from google.adk.tools import ToolContext

from ._state import AirlineAgentContext


def change_seat(
    flight_number: str,
    seat: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Move the passenger to a different seat on a flight.

    Args:
        flight_number: The flight number to change the seat on.
        seat: The new seat to assign to the passenger.

    Returns:
        A dictionary with a message confirming the seat change.
    """

    context: AirlineAgentContext = AirlineAgentContext.model_validate(tool_context.state["context"])

    try:
        message = context.change_seat(flight_number, seat)
    except ValueError as exc:  # translate user errors
        raise ValueError(str(exc)) from exc

    # Persist updated context
    tool_context.state["context"] = context.model_dump()

    return {"result": message}


def cancel_trip(
    tool_context: ToolContext,
) -> dict[str, str]:
    """Cancel the traveller's upcoming trip and note the refund.

    Returns:
        A dictionary with a message confirming the cancellation.
    """

    context: AirlineAgentContext = AirlineAgentContext.model_validate(tool_context.state["context"])

    message = context.cancel_trip()

    # Persist updated context
    tool_context.state["context"] = context.model_dump()

    return {"result": message}


def add_checked_bag(
    tool_context: ToolContext,
) -> dict[str, str | int]:
    """Add a checked bag to the reservation.

    Returns:
        A dictionary with a message confirming the addition and the total bags checked.
    """

    context: AirlineAgentContext = AirlineAgentContext.model_validate(tool_context.state["context"])

    message = context.add_bag()

    # Persist updated context
    tool_context.state["context"] = context.model_dump()

    return {"result": message, "bags_checked": context.customer_profile.bags_checked}


def set_meal_preference(
    meal: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Record or update the passenger's meal preference.

    Args:
        meal: The meal preference to set (e.g. vegetarian).
    Returns:
        A dictionary with a message confirming the meal preference update.
    """

    context: AirlineAgentContext = AirlineAgentContext.model_validate(tool_context.state["context"])

    message = context.set_meal(meal)

    # Persist updated context
    tool_context.state["context"] = context.model_dump()

    return {"result": message}


def request_assistance(
    note: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Note a special assistance request for airport staff.

    Args:
        note: The assistance request details.
    Returns:
        A dictionary with a message confirming the assistance request.
    """

    context: AirlineAgentContext = AirlineAgentContext.model_validate(tool_context.state["context"])

    message = context.request_assistance(note)

    # Persist updated context
    tool_context.state["context"] = context.model_dump()

    return {"result": message}
