from typing import Any, Final, Literal

from google.adk.tools import ToolContext

from ._sample_widget import render_weather_widget, weather_widget_copy_text
from ._state import FactContext
from ._weather import WeatherLookupError, retrieve_weather
from ._weather import normalize_unit as normalize_temperature_unit

SUPPORTED_COLOR_SCHEMES: Final[frozenset[str]] = frozenset({"light", "dark"})
CLIENT_THEME_TOOL_NAME: Final[str] = "switch_theme"


def _normalize_color_scheme(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in SUPPORTED_COLOR_SCHEMES:
        return normalized
    if "dark" in normalized:
        return "dark"
    if "light" in normalized:
        return "light"
    raise ValueError("Theme must be either 'light' or 'dark'.")


async def save_fact(
    fact: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Record a fact shared by the user so it is saved immediately.

    Args:
        fact: A short, declarative statement summarizing a fact shared by the user.

    Returns:
        A dictionary containing the ID and text of the saved fact.
    """

    fact_context: FactContext = FactContext.model_validate(tool_context.state["context"])

    saved = await fact_context.create(text=fact)
    confirmed = await fact_context.mark_saved(saved.id)

    if confirmed is None:
        raise ValueError("Failed to save fact")

    tool_context.state["context"] = fact_context.model_dump()

    return {"fact_id": confirmed.id, "text": confirmed.text}


async def switch_theme(theme: str) -> dict[str, str]:
    """Switch the chat interface between light and dark color schemes.

    Args:
        theme: The requested color scheme, either 'light' or 'dark'.

    Returns:
        A dictionary confirming the applied theme.
    """

    requested = _normalize_color_scheme(theme)
    # ctx.context.client_tool_call = ClientToolCall(
    #     name=CLIENT_THEME_TOOL_NAME,
    #     arguments={"theme": requested},
    # )
    return {"theme": requested}


async def get_weather(
    location: str,
    tool_context: ToolContext,
    unit: Literal["celsius", "fahrenheit"] = "fahrenheit",
) -> dict[str, str]:
    """Look up the current weather and upcoming forecast for a location and render an interactive weather dashboard.

    Args:
        location: The location to look up the weather for.
        unit: The temperature unit to use, either 'celsius' or 'fahrenheit'.


    """
    print("[WeatherTool] tool invoked", {"location": location, "unit": unit})
    try:
        normalized_unit = normalize_temperature_unit(unit)
    except WeatherLookupError as exc:
        print("[WeatherTool] invalid unit", {"error": str(exc)})
        raise ValueError(str(exc)) from exc

    try:
        data = await retrieve_weather(location, normalized_unit)
    except WeatherLookupError as exc:
        print("[WeatherTool] lookup failed", {"error": str(exc)})
        raise ValueError(str(exc)) from exc

    print(
        "[WeatherTool] lookup succeeded",
        {
            "location": data.location,
            "temperature": data.temperature,
            "unit": data.temperature_unit,
        },
    )

    try:
        widget = render_weather_widget(data)
        copy_text = weather_widget_copy_text(data)
        payload: Any
        try:
            payload = widget.model_dump()
        except AttributeError:
            payload = widget
        print("[WeatherTool] widget payload", payload)
    except Exception as exc:  # noqa: BLE001
        print("[WeatherTool] widget build failed", {"error": str(exc)})
        raise ValueError("Weather data is currently unavailable for that location.") from exc

    # print("[WeatherTool] streaming widget")
    # try:
    #     await ctx.context.stream_widget(widget, copy_text=copy_text)
    # except Exception as exc:  # noqa: BLE001
    #     print("[WeatherTool] widget stream failed", {"error": str(exc)})
    #     raise ValueError("Weather data is currently unavailable for that location.") from exc

    # print("[WeatherTool] widget streamed")

    observed = data.observation_time.isoformat() if data.observation_time else None

    result = {"location": data.location, "unit": normalized_unit}

    if observed:
        result["observation_time"] = observed

    return result
