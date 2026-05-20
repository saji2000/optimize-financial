from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+psycopg://advisor:advisor@localhost:5432/advisor_signal_extraction"
    redis_url: str = "redis://localhost:6379/0"
    frontend_api_base_url: str = "http://localhost:8000"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    openai_model_mid: str = "gpt-5.4"
    openai_model_low: str = "gpt-5.4-mini"
    openai_max_output_tokens: int = 2000
    openai_temperature: float | None = None
    openai_pricing_version: str = "2026-05-19"
    openai_model_pricing_usd_per_1m_tokens: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "gpt-5.5": {"input": 5.00, "output": 30.00},
            "gpt-5.4": {"input": 2.50, "output": 15.00},
            "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
        }
    )

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8")


settings = Settings()
