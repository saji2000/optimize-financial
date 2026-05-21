from pydantic import BaseModel, Field


class LLMUsageSummaryRead(BaseModel):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_total_cost_usd: float = 0.0
    retry_count: int = 0
    latest_pricing_version: str | None = None


class LLMUsageStepRead(BaseModel):
    pipeline_step: str
    agent_name: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_total_cost_usd: float = 0.0
    retry_count: int = 0
    models: list[str] = Field(default_factory=list)
    prompt_versions: list[str] = Field(default_factory=list)
