import asyncio

from google.adk.agents import BaseAgent
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService

from ._config import Settings


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
        self._runners: dict[str, Runner] = {}
        self._settings = settings
        self._session_service = session_service

    def add_runner(self, app_name: str, agent: BaseAgent) -> Runner:
        if app_name in self._runners:
            raise ValueError(f"Runner for app '{app_name}' already exists")

        runner = Runner(
            app_name=app_name,
            agent=agent,
            session_service=self._session_service,
        )

        self._runners[app_name] = runner

        return runner

    def get_runner(self, app_name: str) -> Runner:
        runner = self._runners.get(app_name)
        assert runner is not None, f"Runner for app '{app_name}' not found"
        return runner

    async def close(self) -> None:
        await _close_runners(list(self._runners.values()))
        self._runners.clear()
