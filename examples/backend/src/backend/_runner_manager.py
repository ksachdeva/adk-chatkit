import asyncio

from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService

from ._config import Settings
from .agents.temp_agent import TempAgent


def _make_temp_agent(settings: Settings) -> TempAgent:
    return TempAgent(
        llm=LiteLlm(
            model=settings.gpt41_mini_agent.llm.model_name,
            **settings.gpt41_mini_agent.llm.provider_args,
        ),
        generate_content_config=settings.gpt41_mini_agent.generate_content,
    )


async def _close_runners(runners: list[Runner]) -> None:
    cleanup_tasks = [asyncio.create_task(runner.close()) for runner in runners]  # type: ignore
    if cleanup_tasks:
        # Wait for all cleanup tasks with timeout
        done, pending = await asyncio.wait(
            cleanup_tasks,
            timeout=30.0,  # 30 second timeout for cleanup
            return_when=asyncio.ALL_COMPLETED,
        )

        # If any tasks are still pending, log it
        if pending:
            for task in pending:
                task.cancel()


class RunnerManager:
    def __init__(
        self,
        settings: Settings,
        session_service: BaseSessionService,
    ) -> None:
        self._runners: dict[str, Runner] = {
            settings.TEMP_APP_NAME: Runner(
                app_name=settings.TEMP_APP_NAME,
                agent=_make_temp_agent(settings),
                session_service=session_service,
            ),
        }

    def get_runner(self, app_name: str) -> Runner:
        runner = self._runners.get(app_name)
        assert runner is not None, f"Runner for app '{app_name}' not found"
        return runner

    async def close(self) -> None:
        await _close_runners(list(self._runners.values()))
        self._runners.clear()
