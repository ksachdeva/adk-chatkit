import os

from google.adk.models.lite_llm import LiteLlm
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.agents import AgentConfig
from backend.agents.airline import AirlineSupportAgent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("MASTER_ENV_FILE", ".env"),
        env_ignore_empty=True,
        extra="ignore",
    )

    gpt41_agent: AgentConfig


_settings = Settings()  # type: ignore


_airline_support_agent_config = _settings.gpt41_agent

root_agent = AirlineSupportAgent(
    llm=LiteLlm(model=_airline_support_agent_config.llm.model_name, **_airline_support_agent_config.llm.provider_args),
    generate_content_config=_airline_support_agent_config.generate_content,
)
