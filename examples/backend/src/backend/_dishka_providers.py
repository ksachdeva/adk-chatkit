from adk_chatkit import ADKStore
from dishka import Provider, Scope, from_context, provide
from dishka.provider import BaseProvider
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from langchain_core.vectorstores import VectorStore

from ._config import SessionStorageType, Settings
from ._refreshed_session_service import RefreshedSessionService
from ._runner_manager import RunnerManager
from .agents.airline import AirlineSupportChatkitServer
from .agents.facts import FactsChatkitServer
from .agents.knowledge import KnowledgeAssistantChatkitServer, make_vector_store
from .agents.widgets import WidgetsChatkitServer


class SessionServiceProvider(Provider):
    scope = Scope.APP

    settings = from_context(provides=Settings, scope=Scope.APP)

    @provide
    async def get_service(self, settings: Settings) -> BaseSessionService:
        if settings.SESSION_STORAGE_TYPE == SessionStorageType.db:
            return RefreshedSessionService(settings.ADK_DATABASE_URL)  # type: ignore

        return InMemorySessionService()  # type: ignore


class VectorStoreProvider(Provider):
    scope = Scope.APP

    settings = from_context(provides=Settings, scope=Scope.APP)

    @provide
    async def get_vector_store(self, settings: Settings) -> VectorStore:
        if settings.embedder is None:
            raise ValueError("Embedder settings must be provided to create a vector store.")
        return make_vector_store(settings)


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

    knowledge_server_provider = Provider(scope=Scope.APP)
    knowledge_server_provider.from_context(Settings)
    knowledge_server_provider.provide(KnowledgeAssistantChatkitServer)

    widget_server_provider = Provider(scope=Scope.APP)
    widget_server_provider.from_context(Settings)
    widget_server_provider.provide(WidgetsChatkitServer)

    return [
        runner_provider,
        SessionServiceProvider(),
        VectorStoreProvider(),
        adk_store_provider,
        airline_support_server_provider,
        facts_server_provider,
        knowledge_server_provider,
        widget_server_provider,
    ]
