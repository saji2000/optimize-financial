from datetime import UTC, datetime

from pydantic import BaseModel, Field
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal


class LLMUsageEventCreate(BaseModel):
    pipeline_run_id: str | None = None
    transcript_id: str
    chunk_id: str | None = None
    agent_name: str
    pipeline_step: str
    model: str
    prompt_version: str
    pricing_version: str = settings.openai_pricing_version
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_input_cost_usd: float = 0.0
    estimated_output_cost_usd: float = 0.0
    estimated_total_cost_usd: float = 0.0
    latency_ms: int = 0
    retry_count: int = 0
    status: str
    error_type: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMUsageService:
    def __init__(self, session_factory: sessionmaker = SessionLocal) -> None:
        self.session_factory = session_factory

    def record(self, event: LLMUsageEventCreate) -> None:
        from app.db.repositories.llm_usage_repo import LLMUsageEventRepository

        with self.session_factory() as db:
            LLMUsageEventRepository(db).create(event)
            db.commit()

    def list_by_pipeline_run(self, pipeline_run_id: str):
        from app.db.repositories.llm_usage_repo import LLMUsageEventRepository

        with self.session_factory() as db:
            return LLMUsageEventRepository(db).list_by_pipeline_run(pipeline_run_id)

    def list_by_transcript(self, transcript_id: str):
        from app.db.repositories.llm_usage_repo import LLMUsageEventRepository

        with self.session_factory() as db:
            return LLMUsageEventRepository(db).list_by_transcript(transcript_id)
