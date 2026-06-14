from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 2030
    database_url: str = "postgresql+psycopg://advisor:advisor@localhost:2040/advisor_signal_extraction"
    redis_url: str = "redis://localhost:2050/0"
    frontend_api_base_url: str = "http://localhost:2030"
    auth_token_secret: str = "local-development-auth-secret-change-me"
    auth_token_ttl_seconds: int = 8 * 60 * 60
    # Active LLM provider: "deepseek" (default, cost-optimized) or "openai".
    llm_provider: str = "deepseek"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    openai_model_mid: str = "gpt-5.4"
    openai_model_low: str = "gpt-5.4-mini"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"
    deepseek_model_mid: str = "deepseek-v4-flash"
    deepseek_model_low: str = "deepseek-v4-flash"
    openai_max_output_tokens: int = 2000
    openai_temperature: float | None = None
    openai_pricing_version: str = "2026-06-14-deepseek"
    sentry_dsn: str = ""
    sentry_enabled: bool = True
    sentry_environment: str = "local"
    sentry_release: str = ""
    sentry_enable_logs: bool = True
    sentry_send_default_pii: bool = False
    sentry_traces_sample_rate: float = 0.1
    sentry_profile_session_sample_rate: float = 0.0
    openai_model_pricing_usd_per_1m_tokens: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "gpt-5.5": {"input": 5.00, "output": 30.00},
            "gpt-5.4": {"input": 2.50, "output": 15.00},
            "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
            # DeepSeek V4 list rates (USD per 1M tokens). "input" is the
            # cache-miss rate; "input_cache_hit" is billed for cached prompt
            # tokens. https://api-docs.deepseek.com/quick_start/pricing
            "deepseek-v4-flash": {
                "input": 0.14,
                "input_cache_hit": 0.0028,
                "output": 0.28,
            },
            "deepseek-v4-pro": {
                "input": 0.435,
                "input_cache_hit": 0.003625,
                "output": 0.87,
            },
        }
    )

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    @property
    def active_model(self) -> str:
        """High-tier model for the active provider."""
        if self.llm_provider == "deepseek":
            return self.deepseek_model
        return self.openai_model

    @property
    def active_model_mid(self) -> str:
        """Mid-tier model for the active provider."""
        if self.llm_provider == "deepseek":
            return self.deepseek_model_mid
        return self.openai_model_mid

    @property
    def active_model_low(self) -> str:
        """Low-tier model for the active provider."""
        if self.llm_provider == "deepseek":
            return self.deepseek_model_low
        return self.openai_model_low


settings = Settings()
