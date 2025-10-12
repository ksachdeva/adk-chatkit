import os
from typing import Annotated, Any, Literal

from pydantic import AnyUrl, BeforeValidator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .agents._config import AgentConfig


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("MASTER_ENV_FILE", ".env"),
        env_ignore_empty=True,
        extra="ignore",
    )

    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        origins = [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]
        origins = origins + [self.FRONTEND_HOST]

        origins.append("http://localhost:5173")
        origins.append("http://localhost:5174")
        origins.append("http://localhost:3000")
        origins.append("http://0.0.0.0:5173")
        origins.append("http://0.0.0.0:3000")

        return origins

    PROJECT_NAME: str = "chatkit-backend-example"

    check_expiration: bool = True

    gpt41_agent: AgentConfig
    gpt41_mini_agent: AgentConfig

    AIRLINE_APP_NAME: str = "airline-support"
