from dishka import Provider, Scope, from_context, provide
from dishka.provider import BaseProvider
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from ._config import Settings
from ._runner_manager import RunnerManager
from .agents.airline import AirlineSupportProcessor


class SessionServiceProvider(Provider):
    scope = Scope.APP

    settings = from_context(provides=Settings, scope=Scope.APP)

    @provide
    async def get_service(self, settings: Settings) -> BaseSessionService:
        return InMemorySessionService()  # type: ignore


def get_providers() -> list[BaseProvider]:
    runner_provider = Provider(scope=Scope.APP)
    runner_provider.from_context(Settings)
    runner_provider.provide(RunnerManager)

    airline_support_processor_provider = Provider(scope=Scope.APP)
    airline_support_processor_provider.from_context(Settings)
    airline_support_processor_provider.provide(AirlineSupportProcessor)

    return [
        runner_provider,
        SessionServiceProvider(),
        airline_support_processor_provider,
    ]
