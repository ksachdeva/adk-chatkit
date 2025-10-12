from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types as genai_types
from pydantic import BaseModel

from backend._runner_manager import RunnerManager

router = APIRouter(route_class=DishkaRoute)


class AgentRunRequest(BaseModel):
    app_name: str
    message: str
    session_id: str
    streaming: bool = False


class MessageResponse(BaseModel):
    content: str
    agent: str
    invocation_id: str


class AgentRunResponse(BaseModel):
    messages: list[MessageResponse]


@router.post(
    "/run",
    summary="Run an Agent",
    response_model=AgentRunResponse,
)
async def chat_completion(
    run_request: AgentRunRequest,
    session_service: FromDishka[BaseSessionService],
    runner_manager: FromDishka[RunnerManager],
) -> AgentRunResponse:
    # hard coded user id for now
    # as not doing an authentication
    user_id = "ksachdeva-1"

    session = await session_service.get_session(
        app_name=run_request.app_name,
        user_id=user_id,
        session_id=run_request.session_id,
    )

    if not session:
        session = await session_service.create_session(
            app_name=run_request.app_name,
            user_id=user_id,
            session_id=run_request.session_id,
        )

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=run_request.message)],
    )

    messages: list[MessageResponse] = []
    runner: Runner = runner_manager.get_runner(run_request.app_name)

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts and event.content.parts[0].text:
            author = event.author
            text = event.content.parts[0].text
            messages.append(
                MessageResponse(
                    content=text,
                    invocation_id=event.invocation_id,
                    agent=author,
                )
            )

    return AgentRunResponse(messages=messages)
