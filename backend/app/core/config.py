from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://advisor:advisor@localhost:5432/advisor_signal_extraction"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8")


settings = Settings()

