from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from adk_chatkit import ChatkitRunConfig, stream_event, stream_widget
from chatkit.types import AssistantMessageContent, AssistantMessageItem, ClientEffectEvent, ThreadItemDoneEvent
from google.adk.tools.tool_context import ToolContext
from pydantic import ValidationError

from ._state import CatAgentContext
from .widgets.name_suggestions_widget import CatNameSuggestion, build_name_suggestions_widget
from .widgets.profile_card_widget import build_profile_card_widget


async def _stream_client_effect(
    tool_context: ToolContext,
    name: str,
    data: dict[str, object],
) -> None:
    """Helper function to create and stream a ClientEffectEvent."""
    event = ClientEffectEvent(name=name, data=data)
    await stream_event(event, tool_context)


async def get_cat_status(tool_context: ToolContext) -> dict[str, Any]:
    """Read the cat's current stats before deciding what to do next. No parameters.

    Returns:
        A dictionary containing the cat's current state.
    """
    print("[TOOL CALL] get_cat_status")
    context = tool_context.state.get("context", None)
    if context is None:
        cat_context = CatAgentContext.create_initial_context()
        tool_context.state["context"] = cat_context.model_dump()
        return cat_context.to_payload()

    cat_context = CatAgentContext.model_validate(context)
    return cat_context.to_payload()


async def feed_cat(
    tool_context: ToolContext,
    meal: Optional[str] = None,
) -> dict[str, str | bool]:
    """Feed the cat to replenish energy and keep moods stable.

    Args:
        meal: Meal or snack description to include in the update.

    Returns:
        A dictionary with a message confirming the feed action.
    """
    print("[TOOL CALL] feed_cat")
    context = CatAgentContext.model_validate(tool_context.state["context"])
    context.feed()
    tool_context.state["context"] = context.model_dump()
    flash = f"Fed {context.name} {meal}" if meal else f"{context.name} enjoyed a snack"

    # Stream update_cat_status event to update frontend UI
    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        thread = run_config.context.thread
        await _stream_client_effect(
            tool_context,
            name="update_cat_status",
            data={
                "state": context.to_payload(thread.id),
                "flash": flash,
            },
        )

    return {"success": True, "result": flash}


async def play_with_cat(
    tool_context: ToolContext,
    activity: Optional[str] = None,
) -> dict[str, str | bool]:
    """Play with the cat to boost happiness and create fun moments.

    Args:
        activity: Toy or activity used during playtime.

    Returns:
        A dictionary with a message confirming the play action.
    """
    print("[TOOL CALL] play_with_cat")
    context = CatAgentContext.model_validate(tool_context.state["context"])
    context.play()
    tool_context.state["context"] = context.model_dump()
    flash = activity or "Playtime"

    # Stream update_cat_status event to update frontend UI
    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        thread = run_config.context.thread
        await _stream_client_effect(
            tool_context,
            name="update_cat_status",
            data={
                "state": context.to_payload(thread.id),
                "flash": f"{context.name} played: {flash}",
            },
        )

    return {"success": True, "result": f"{context.name} played: {flash}"}


async def clean_cat(
    tool_context: ToolContext,
    method: Optional[str] = None,
) -> dict[str, str | bool]:
    """Clean the cat to tidy up and improve cleanliness.

    Args:
        method: Cleaning method or item used.

    Returns:
        A dictionary with a message confirming the clean action.
    """
    print("[TOOL CALL] clean_cat")
    context = CatAgentContext.model_validate(tool_context.state["context"])
    context.clean()
    tool_context.state["context"] = context.model_dump()
    flash = method or "Bath time"

    # Stream update_cat_status event to update frontend UI
    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        thread = run_config.context.thread
        await _stream_client_effect(
            tool_context,
            name="update_cat_status",
            data={
                "state": context.to_payload(thread.id),
                "flash": f"{context.name} is fresh: {flash}",
            },
        )
    return {"success": True, "result": f"{context.name} is fresh: {flash}"}


async def set_cat_name(
    name: str,
    tool_context: ToolContext,
) -> dict[str, str | bool]:
    """Give the cat a permanent name and update the thread title to match.

    Args:
        name: Desired name for the cat.

    Returns:
        A dictionary with a message confirming the name change.
    """
    print(f'[TOOL CALL] set_cat_name("{name}")')

    context = CatAgentContext.model_validate(tool_context.state["context"])
    if context.name != "Unnamed Cat":
        # Stream a message when cat already has a name
        run_config = tool_context._invocation_context.run_config
        if isinstance(run_config, ChatkitRunConfig):
            thread = run_config.context.thread
            message_item = AssistantMessageItem(
                id=uuid4().hex,
                thread_id=thread.id,
                created_at=datetime.now(),
                content=[AssistantMessageContent(text=f"{context.name} is ready to play!")],
            )
            await stream_event(ThreadItemDoneEvent(item=message_item), tool_context)
        return {"success": False, "result": f"{context.name} already has a name and cannot be renamed."}

    cleaned = name.strip().title()
    if not cleaned:
        raise ValueError("A name is required to name the cat.")

    context.rename(cleaned)
    tool_context.state["context"] = context.model_dump()

    # Stream update_cat_status event to update frontend UI
    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        thread = run_config.context.thread
        await _stream_client_effect(
            tool_context,
            name="update_cat_status",
            data={
                "state": context.to_payload(thread.id),
                "flash": f"Now called {context.name}",
            },
        )

    return {"success": True, "result": f"Cat is now named {context.name}"}


async def show_cat_profile(
    tool_context: ToolContext,
    age: Optional[int] = None,
    favorite_toy: Optional[str] = None,
) -> dict[str, str | bool]:
    """Show the cat's profile card with avatar and age.

    Args:
        age: Cat age (in years) to display and persist.
        favorite_toy: Favorite toy label to include.

    Returns:
        A dictionary with a message confirming the profile display.
    """
    print("[TOOL CALL] show_cat_profile")

    context = CatAgentContext.model_validate(tool_context.state["context"])
    context.set_age(age)
    tool_context.state["context"] = context.model_dump()

    widget = build_profile_card_widget(context, favorite_toy)
    await stream_widget(widget, tool_context)

    # Stream a message after showing the profile
    run_config = tool_context._invocation_context.run_config
    if isinstance(run_config, ChatkitRunConfig):
        thread = run_config.context.thread
        if context.name == "Unnamed Cat":
            message_text = "Would you like to give your cat a name?"
        else:
            message_text = f"License checked! Would you like to feed, play with, or clean {context.name}?"

        message_item = AssistantMessageItem(
            id=uuid4().hex,
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[AssistantMessageContent(text=message_text)],
        )
        await stream_event(ThreadItemDoneEvent(item=message_item), tool_context)

    if context.name == "Unnamed Cat":
        return {"success": True, "result": "Profile displayed. Would you like to give your cat a name?"}

    return {
        "success": True,
        "result": f"License checked! Would you like to feed, play with, or clean {context.name}?",
    }


async def speak_as_cat(
    line: str,
    tool_context: ToolContext,
) -> dict[str, str | bool]:
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

    # Get current cat state to include in the effect
    context = CatAgentContext.model_validate(tool_context.state["context"])

    # Stream the client effect event to trigger the speech bubble
    await _stream_client_effect(
        tool_context,
        name="cat_say",
        data={
            "message": message,
            "state": context.to_payload(),
        },
    )

    return {"success": True, "result": f"Cat said: {message}"}


async def suggest_cat_names(
    suggestions: list[dict[str, Any]],
    tool_context: ToolContext,
) -> dict[str, str | bool]:
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

        # Stream a message before showing the widget
        run_config = tool_context._invocation_context.run_config
        if isinstance(run_config, ChatkitRunConfig):
            thread = run_config.context.thread
            message_item = AssistantMessageItem(
                id=uuid4().hex,
                thread_id=thread.id,
                created_at=datetime.now(),
                content=[AssistantMessageContent(text="Here are some name suggestions for your cat.")],
            )
            await stream_event(ThreadItemDoneEvent(item=message_item), tool_context)

        widget = build_name_suggestions_widget(normalized)
        await stream_widget(widget, tool_context)

        return {"success": True, "result": "Name suggestions displayed."}
    except Exception as exc:
        print(f"[TOOL CALL] Error suggesting cat names: {exc}")
        raise
