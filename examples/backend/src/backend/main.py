import logging

from dishka import make_async_container
from dishka.integrations.fastapi import (
    setup_dishka,
)

from backend._app import App
from backend._config import Settings
from backend._dishka_providers import get_providers

_LOGGER = logging.getLogger("uvicorn")


def create_app(settings: Settings) -> App:
    app = App(settings=settings)
    setup_dishka(container, app)
    return app


# Create the settings
settings = Settings()  # type: ignore
_LOGGER.info(f"Settings: {settings}")


# Make the container with settings in context
container = make_async_container(
    *get_providers(),
    context={
        Settings: settings,
    },
)

# Make the app
app = create_app(settings)
