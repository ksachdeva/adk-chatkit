from __future__ import annotations

from typing import Any, Optional

from adk_chatkit import stream_widget
from google.adk.tools.tool_context import ToolContext
from pydantic import ValidationError

from ._state import CatAgentContext, CatState
from .widgets.name_suggestions_widget import CatNameSuggestion, build_name_suggestions_widget
from .widgets.profile_card_widget import build_profile_card_widget


def _get_state(tool_context: ToolContext) -> CatState:
    """Get the current cat state from the session."""
    context = tool_context.state.get("context", None)
    if context is None:
        cat_context = CatAgentContext.create_initial_context()
        tool_context.state["context"] = cat_context.model_dump()
        return CatState.from_dict(cat_context.cat_state)

    cat_context = CatAgentContext.model_validate(context)
    return CatState.from_dict(cat_context.cat_state)


def _update_state(tool_context: ToolContext, mutator: Any) -> CatState:
    """Update the cat state using a mutator function."""
    state = _get_state(tool_context)
    mutator(state)
    context = CatAgentContext(cat_state=state.to_dict())
    tool_context.state["context"] = context.model_dump()
    return state


async def get_cat_status(tool_context: ToolContext) -> dict[str, Any]:
    """Read the cat's current stats before deciding what to do next. No parameters.

    Returns:
        A dictionary containing the cat's current state.
    """
    print("[TOOL CALL] get_cat_status")
    state = _get_state(tool_context)
    return state.to_payload()


async def feed_cat(
    tool_context: ToolContext,
    meal: Optional[str] = None,
) -> dict[str, str]:
    """Feed the cat to replenish energy and keep moods stable.

    Args:
        meal: Meal or snack description to include in the update.

    Returns:
        A dictionary with a message confirming the feed action.
    """
    print("[TOOL CALL] feed_cat")
    state = _update_state(tool_context, lambda s: s.feed())
    flash = f"Fed {state.name} {meal}" if meal else f"{state.name} enjoyed a snack"
    return {"result": flash}


async def play_with_cat(
    tool_context: ToolContext,
    activity: Optional[str] = None,
) -> dict[str, str]:
    """Play with the cat to boost happiness and create fun moments.

    Args:
        activity: Toy or activity used during playtime.

    Returns:
        A dictionary with a message confirming the play action.
    """
    print("[TOOL CALL] play_with_cat")
    state = _update_state(tool_context, lambda s: s.play())
    flash = activity or "Playtime"
    return {"result": f"{state.name} played: {flash}"}


async def clean_cat(
    tool_context: ToolContext,
    method: Optional[str] = None,
) -> dict[str, str]:
    """Clean the cat to tidy up and improve cleanliness.

    Args:
        method: Cleaning method or item used.

    Returns:
        A dictionary with a message confirming the clean action.
    """
    print("[TOOL CALL] clean_cat")
    state = _update_state(tool_context, lambda s: s.clean())
    flash = method or "Bath time"
    return {"result": f"{state.name} is fresh: {flash}"}


async def set_cat_name(
    name: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Give the cat a permanent name and update the thread title to match.

    Args:
        name: Desired name for the cat.

    Returns:
        A dictionary with a message confirming the name change.
    """
    print(f'[TOOL CALL] set_cat_name("{name}")')

    state = _get_state(tool_context)
    if state.name != "Unnamed Cat":
        return {"result": f"{state.name} already has a name and cannot be renamed."}

    cleaned = name.strip().title()
    if not cleaned:
        raise ValueError("A name is required to name the cat.")

    state = _update_state(tool_context, lambda s: s.rename(cleaned))
    return {"result": f"Cat is now named {state.name}"}


async def show_cat_profile(
    tool_context: ToolContext,
    age: Optional[int] = None,
    favorite_toy: Optional[str] = None,
) -> dict[str, str]:
    """Show the cat's profile card with avatar and age.

    Args:
        age: Cat age (in years) to display and persist.
        favorite_toy: Favorite toy label to include.

    Returns:
        A dictionary with a message confirming the profile display.
    """
    print("[TOOL CALL] show_cat_profile")

    def mutate(state: CatState) -> None:
        state.set_age(age)

    state = _update_state(tool_context, mutate)
    widget = build_profile_card_widget(state, favorite_toy)
    await stream_widget(widget, tool_context)

    if state.name == "Unnamed Cat":
        return {"result": "Profile displayed. Would you like to give your cat a name?"}

    return {"result": f"License checked! Would you like to feed, play with, or clean {state.name}?"}


async def speak_as_cat(
    line: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Speak as the cat so a bubble appears in the dashboard.

    Args:
        line: The text the cat should say.

    Returns:
        A dictionary with a message confirming the cat speech.
    """
    print(f"[TOOL CALL] speak_as_cat({line})")
    message = line.strip()
    if not message:
        raise ValueError("A line is required for the cat to speak.")

    return {"result": f"Cat said: {message}"}


async def suggest_cat_names(
    suggestions: list[dict[str, Any]],
    tool_context: ToolContext,
) -> dict[str, str]:
    """Render up to three creative cat name options provided in the `suggestions` argument.

    Args:
        suggestions: List of name suggestions with a `name` and `reason` for each.

    Returns:
        A dictionary with a message confirming the suggestions.
    """
    print("[TOOL CALL] suggest_cat_names")
    try:
        normalized: list[CatNameSuggestion] = []
        for entry in suggestions:
            try:
                normalized.append(
                    entry if isinstance(entry, CatNameSuggestion) else CatNameSuggestion.model_validate(entry)
                )
            except ValidationError as exc:
                print(f"[TOOL CALL] Invalid name suggestion payload: {exc}")
        if not normalized:
            raise ValueError("Provide at least one valid name suggestion before calling the tool.")

        widget = build_name_suggestions_widget(normalized)
        await stream_widget(widget, tool_context)

        return {"result": "Name suggestions displayed."}
    except Exception as exc:
        print(f"[TOOL CALL] Error suggesting cat names: {exc}")
        raise
