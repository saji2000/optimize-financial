from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db.repositories.llm_usage_repo import LLMUsageEventRepository
from app.db.repositories.pipeline_run_repo import PipelineRunRepository
from app.db.repositories.transcript_repo import TranscriptRepository
from app.services.llm_usage_service import LLMUsageEventCreate
from app.services.pipeline_service import get_pipeline_run
from app.services.transcript_service import list_transcripts


def test_transcript_usage_summary_aggregates_events(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as db:
        transcript = TranscriptRepository(db).create(
            title="Sanitized usage call",
            raw_text="sanitized transcript",
        )
        run = PipelineRunRepository(db).create(transcript_id=transcript.id)
        usage_repo = LLMUsageEventRepository(db)
        usage_repo.create(
            LLMUsageEventCreate(
                pipeline_run_id=run.id,
                transcript_id=transcript.id,
                agent_name="SignalExtractionAgent",
                pipeline_step="segment_signal_extraction",
                model="gpt-5.4",
                prompt_version="signal_extraction_v1",
                pricing_version="2026-05-01",
                input_tokens=100,
                output_tokens=20,
                total_tokens=120,
                estimated_total_cost_usd=0.012,
                retry_count=1,
                status="success",
                created_at=datetime(2026, 5, 20, tzinfo=UTC),
            )
        )
        usage_repo.create(
            LLMUsageEventCreate(
                pipeline_run_id=run.id,
                transcript_id=transcript.id,
                agent_name="SignalExtractionAgent",
                pipeline_step="segment_signal_extraction",
                model="gpt-5.4",
                prompt_version="signal_extraction_v1",
                pricing_version="2026-05-02",
                retry_count=2,
                status="failed",
                error_type="RateLimitError",
                created_at=datetime(2026, 5, 20, tzinfo=UTC) + timedelta(minutes=1),
            )
        )
        db.commit()

        row = list_transcripts(db)[0]

    assert row.usage.calls == 2
    assert row.usage.input_tokens == 100
    assert row.usage.output_tokens == 20
    assert row.usage.total_tokens == 120
    assert row.usage.estimated_total_cost_usd == pytest.approx(0.012)
    assert row.usage.retry_count == 3
    assert row.usage.latest_pricing_version == "2026-05-02"


def test_pipeline_run_usage_summary_and_steps_aggregate_events(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as db:
        transcript = TranscriptRepository(db).create(
            title="Sanitized pipeline call",
            raw_text="sanitized transcript",
        )
        run = PipelineRunRepository(db).create(transcript_id=transcript.id)
        usage_repo = LLMUsageEventRepository(db)
        usage_repo.create(
            LLMUsageEventCreate(
                pipeline_run_id=run.id,
                transcript_id=transcript.id,
                agent_name="SignalExtractionAgent",
                pipeline_step="segment_signal_extraction",
                model="gpt-5.4",
                prompt_version="signal_extraction_v1",
                input_tokens=50,
                output_tokens=10,
                total_tokens=60,
                estimated_total_cost_usd=0.006,
                retry_count=1,
                status="success",
            )
        )
        usage_repo.create(
            LLMUsageEventCreate(
                pipeline_run_id=run.id,
                transcript_id=transcript.id,
                agent_name="SignalExtractionAgent",
                pipeline_step="segment_signal_extraction",
                model="gpt-5.5",
                prompt_version="signal_extraction_v1",
                input_tokens=40,
                output_tokens=8,
                total_tokens=48,
                estimated_total_cost_usd=0.004,
                status="success",
            )
        )
        usage_repo.create(
            LLMUsageEventCreate(
                pipeline_run_id=run.id,
                transcript_id=transcript.id,
                agent_name="EvidenceValidationAgent",
                pipeline_step="evidence_validation",
                model="gpt-5.5",
                prompt_version="evidence_validation_v1",
                input_tokens=20,
                output_tokens=5,
                total_tokens=25,
                estimated_total_cost_usd=0.002,
                status="success",
            )
        )
        db.commit()

        read = get_pipeline_run(run.id, db)

    assert read.usage.calls == 3
    assert read.usage.input_tokens == 110
    assert read.usage.output_tokens == 23
    assert read.usage.estimated_total_cost_usd == pytest.approx(0.012)
    extraction = next(
        step for step in read.usage_by_step if step.pipeline_step == "segment_signal_extraction"
    )
    assert extraction.agent_name == "SignalExtractionAgent"
    assert extraction.calls == 2
    assert extraction.models == ["gpt-5.4", "gpt-5.5"]
    assert extraction.prompt_versions == ["signal_extraction_v1"]
