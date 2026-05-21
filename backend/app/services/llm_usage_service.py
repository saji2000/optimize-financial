from datetime import UTC, datetime

from pydantic import BaseModel, Field
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.llm_usage_event import LLMUsageEvent
from app.db.session import SessionLocal
from app.domain.usage_schema import LLMUsageStepRead, LLMUsageSummaryRead


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


def summarize_usage(events: list[LLMUsageEvent]) -> LLMUsageSummaryRead:
    latest_event = max(events, key=lambda event: event.created_at, default=None)
    return LLMUsageSummaryRead(
        calls=len(events),
        input_tokens=sum(event.input_tokens for event in events),
        output_tokens=sum(event.output_tokens for event in events),
        total_tokens=sum(event.total_tokens for event in events),
        estimated_total_cost_usd=sum(event.estimated_total_cost_usd for event in events),
        retry_count=sum(event.retry_count for event in events),
        latest_pricing_version=latest_event.pricing_version if latest_event else None,
    )


def summarize_usage_by_step(events: list[LLMUsageEvent]) -> list[LLMUsageStepRead]:
    grouped: dict[tuple[str, str], list[LLMUsageEvent]] = {}
    for event in events:
        grouped.setdefault((event.pipeline_step, event.agent_name), []).append(event)

    rows: list[LLMUsageStepRead] = []
    for (pipeline_step, agent_name), step_events in grouped.items():
        rows.append(
            LLMUsageStepRead(
                pipeline_step=pipeline_step,
                agent_name=agent_name,
                calls=len(step_events),
                input_tokens=sum(event.input_tokens for event in step_events),
                output_tokens=sum(event.output_tokens for event in step_events),
                total_tokens=sum(event.total_tokens for event in step_events),
                estimated_total_cost_usd=sum(
                    event.estimated_total_cost_usd for event in step_events
                ),
                retry_count=sum(event.retry_count for event in step_events),
                models=sorted({event.model for event in step_events}),
                prompt_versions=sorted({event.prompt_version for event in step_events}),
            )
        )
    return sorted(rows, key=lambda row: row.pipeline_step)
