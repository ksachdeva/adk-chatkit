import functools
from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncGenerator, Callable, Self

import fastapi
from fastapi import FastAPI
from google.adk.runners import Runner
from starlette.middleware.cors import CORSMiddleware

from ._config import Settings
from ._runner_manager import RunnerManager
from .api.cat import router as cat_router
from .api.facts import router as facts_router
from .api.health import router as health_router
from .api.knowledge import router as knowledge_router
from .api.metro_map import router as metro_map_router
from .api.news import router as news_router
from .api.support import router as support_router
from .api.widgets import router as widgets_router


@asynccontextmanager
async def internal_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    finally:
        runner_manager = await app.state.dishka_container.get(RunnerManager)
        await runner_manager.close()
        await app.state.dishka_container.close()


class App(fastapi.FastAPI):
    def __init__(
        self,
        settings: Settings,
        lifespan: Callable[[Self], AsyncContextManager[None]] | None = None,
    ):
        self._runner_cache: dict[str, Runner] = {}

        lifespan = functools.partial(internal_lifespan)

        super().__init__(
            title=settings.PROJECT_NAME,
            docs_url="/docs" if settings.ENVIRONMENT in ["local", "staging"] else None,
            redoc_url=None,
            lifespan=lifespan,
        )

        if settings.all_cors_origins:
            self.add_middleware(
                CORSMiddleware,
                allow_origins=settings.all_cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        self.include_router(health_router, tags=["healthcheck"])
        self.include_router(support_router, prefix="/support", tags=["support"])
        self.include_router(facts_router, prefix="/facts", tags=["facts"])
        self.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
        self.include_router(widgets_router, prefix="/widgets", tags=["widgets"])
        self.include_router(cat_router, prefix="/cat", tags=["cat"])
        self.include_router(news_router, prefix="/news", tags=["news"])
        self.include_router(metro_map_router, prefix="/metro-map", tags=["metro-map"])
