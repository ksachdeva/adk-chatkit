from adk_chatkit import ADKStore
from dishka import Provider, Scope, from_context, provide
from dishka.provider import BaseProvider
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from ._config import SessionStorageType, Settings
from ._runner_manager import RunnerManager
from .agents.airline import AirlineSupportChatkitServer
from .agents.facts import FactsChatkitServer


class SessionServiceProvider(Provider):
    scope = Scope.APP

    settings = from_context(provides=Settings, scope=Scope.APP)

    @provide
    async def get_service(self, settings: Settings) -> BaseSessionService:
        if settings.SESSION_STORAGE_TYPE == SessionStorageType.db:
            return DatabaseSessionService(settings.ADK_DATABASE_URL)  # type: ignore

        return InMemorySessionService()  # type: ignore


def get_providers() -> list[BaseProvider]:
    runner_provider = Provider(scope=Scope.APP)
    runner_provider.from_context(Settings)
    runner_provider.provide(RunnerManager)

    adk_store_provider = Provider(scope=Scope.APP)
    adk_store_provider.provide(ADKStore)

    airline_support_server_provider = Provider(scope=Scope.APP)
    airline_support_server_provider.from_context(Settings)
    airline_support_server_provider.provide(AirlineSupportChatkitServer)

    facts_server_provider = Provider(scope=Scope.APP)
    facts_server_provider.from_context(Settings)
    facts_server_provider.provide(FactsChatkitServer)

    return [
        runner_provider,
        SessionServiceProvider(),
        adk_store_provider,
        airline_support_server_provider,
        facts_server_provider,
    ]
