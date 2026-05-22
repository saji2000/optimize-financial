import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db.repositories.pipeline_run_repo import PipelineRunRepository
from app.db.repositories.signal_repo import SignalRepository
from app.db.repositories.transcript_repo import TranscriptRepository
from app.pipeline.schemas import FinalSignal, PipelineOutputs, PreparedTranscript, TranscriptChunk, TranscriptTurn
from app.workers import tasks


class FakeOrchestrator:
    seen_pipeline_run_ids: list[str | None] = []

    def __init__(self, pipeline_run_id: str | None = None) -> None:
        self.seen_pipeline_run_ids.append(pipeline_run_id)

    def run_outputs(self, transcript_id: str, raw_text: str) -> PipelineOutputs:
        assert raw_text == "00:01:00 Advisor: I need stronger support."
        prepared = PreparedTranscript(
            transcript_id=transcript_id,
            chunks=[
                TranscriptChunk(
                    transcript_id=transcript_id,
                    chunk_id=f"{transcript_id}_chunk_001",
                    turns=[
                        TranscriptTurn(
                            sequence=1,
                            timestamp="00:01:00",
                            end_timestamp=None,
                            speaker="Advisor",
                            speaker_role="advisor",
                            text="I need stronger support.",
                        )
                    ],
                )
            ],
        )
        return PipelineOutputs(
            prepared_transcript=prepared,
            final_signals=[
                FinalSignal(
                    transcript_id=transcript_id,
                    item_type="driver",
                    rank=1,
                    category="Operational support",
                    advisor_quote="I need stronger support.",
                    timestamp="00:01:00",
                    evidence_strength="explicit",
                    rationale="The advisor states a support need.",
                )
            ],
        )


class FailingOrchestrator:
    def __init__(self, pipeline_run_id: str | None = None) -> None:
        self.pipeline_run_id = pipeline_run_id

    def run_outputs(self, transcript_id: str, raw_text: str) -> PipelineOutputs:
        raise RuntimeError("SECRET TRANSCRIPT TEXT")


def test_worker_runs_orchestrator_and_persists_outputs(
    db_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    monkeypatch.setattr(tasks, "SessionLocal", db_session_factory)
    monkeypatch.setattr(tasks, "PipelineOrchestrator", FakeOrchestrator)
    FakeOrchestrator.seen_pipeline_run_ids = []
    with db_session_factory() as db:
        transcript = TranscriptRepository(db).create(
            title="Sanitized call",
            raw_text="00:01:00 Advisor: I need stronger support.",
        )
        run = PipelineRunRepository(db).create(transcript_id=transcript.id)
        db.commit()
        transcript_id = transcript.id
        run_id = run.id

    result = tasks.run_transcript_pipeline.run(transcript_id, run_id)

    assert result == {
        "status": "completed",
        "transcript_id": transcript_id,
        "pipeline_run_id": run_id,
    }
    assert FakeOrchestrator.seen_pipeline_run_ids == [run_id]
    with db_session_factory() as db:
        transcript = TranscriptRepository(db).get(transcript_id)
        run = PipelineRunRepository(db).get(run_id)
        signals = SignalRepository(db).list_final_signals(transcript_id=transcript_id)
        assert transcript is not None
        assert transcript.status == "completed"
        assert run is not None
        assert run.status == "completed"
        assert len(signals) == 1


def test_worker_failure_persists_sanitized_error_metadata(
    db_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    captured = []
    monkeypatch.setattr(tasks, "SessionLocal", db_session_factory)
    monkeypatch.setattr(tasks, "PipelineOrchestrator", FailingOrchestrator)
    monkeypatch.setattr(
        tasks,
        "capture_sanitized_exception",
        lambda error, **kwargs: captured.append({"error": error, **kwargs}),
    )
    with db_session_factory() as db:
        transcript = TranscriptRepository(db).create(
            title="Sanitized call",
            raw_text="00:01:00 Advisor: I need stronger support.",
        )
        run = PipelineRunRepository(db).create(transcript_id=transcript.id)
        db.commit()
        transcript_id = transcript.id
        run_id = run.id

    with pytest.raises(RuntimeError):
        tasks.run_transcript_pipeline.run(transcript_id, run_id)

    with db_session_factory() as db:
        transcript = TranscriptRepository(db).get(transcript_id)
        run = PipelineRunRepository(db).get(run_id)
        assert transcript is not None
        assert run is not None
        assert transcript.status == "failed"
        assert run.status == "failed"
        assert transcript.error_type == "RuntimeError"
        assert run.error_message == "Pipeline failed with RuntimeError."
        assert "SECRET" not in transcript.error_message

    assert len(captured) == 1
    assert captured[0]["pipeline_run_id"] == run_id
    assert captured[0]["transcript_id"] == transcript_id
    assert captured[0]["agent_name"] == "PipelineOrchestrator"
    assert captured[0]["pipeline_step"] == "worker_task"
    assert "SECRET" not in str({key: value for key, value in captured[0].items() if key != "error"})
