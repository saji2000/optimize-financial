from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.db.repositories.llm_usage_repo import LLMUsageEventRepository
from app.db.repositories.pipeline_run_repo import PipelineRunRepository
from app.main import app
from app.pipeline.persistence import persist_pipeline_outputs
from app.pipeline.schemas import FinalSignal, PreparedTranscript, TranscriptChunk, TranscriptTurn
from app.security.auth import CURTIS_USER, create_access_token
from app.services.llm_usage_service import LLMUsageEventCreate


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(CURTIS_USER)}"}


def test_protected_routes_require_login() -> None:
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/transcripts").status_code == 401
    assert client.post("/auth/login", json={"username": "curtis", "password": "wrong"}).status_code == 401


def test_transcript_upload_detail_signals_and_pipeline_runs(
    db_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    enqueued: list[tuple[str, str | None]] = []

    def fake_queue_pipeline_run(transcript_id: str, pipeline_run_id: str | None = None) -> None:
        enqueued.append((transcript_id, pipeline_run_id))

    def override_get_db() -> Iterator[Session]:
        with db_session_factory() as db:
            yield db

    monkeypatch.setattr("app.api.routes.transcripts.queue_pipeline_run", fake_queue_pipeline_run)
    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        headers = auth_headers()
        response = client.post(
            "/transcripts",
            headers=headers,
            files={"file": ("call.txt", "00:01:00 Advisor: I need stronger support.", "text/plain")},
            data={"title": "Sanitized call"},
        )
        assert response.status_code == 202
        transcript = response.json()
        assert transcript["title"] == "Sanitized call"
        assert transcript["status"] == "queued"
        assert enqueued and enqueued[0][0] == transcript["id"]

        with db_session_factory() as db:
            prepared = PreparedTranscript(
                transcript_id=transcript["id"],
                chunks=[
                    TranscriptChunk(
                        transcript_id=transcript["id"],
                        chunk_id=f"{transcript['id']}_chunk_001",
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
            final = [
                FinalSignal(
                    transcript_id=transcript["id"],
                    item_type="driver",
                    rank=1,
                    category="Operational support",
                    advisor_quote="I need stronger support.",
                    timestamp="00:01:00",
                    evidence_strength="explicit",
                    rationale="The advisor states a support need.",
                )
            ]
            persist_pipeline_outputs(db, prepared_transcript=prepared, final_signals=final)
            pipeline_run_id = PipelineRunRepository(db).list()[0].id
            LLMUsageEventRepository(db).create(
                LLMUsageEventCreate(
                    pipeline_run_id=pipeline_run_id,
                    transcript_id=transcript["id"],
                    agent_name="SignalExtractionAgent",
                    pipeline_step="segment_signal_extraction",
                    model="gpt-5.4",
                    prompt_version="signal_extraction_v1",
                    pricing_version="2026-05-20",
                    input_tokens=100,
                    output_tokens=20,
                    total_tokens=120,
                    estimated_total_cost_usd=0.012,
                    retry_count=1,
                    status="success",
                    created_at=datetime(2026, 5, 20, tzinfo=UTC),
                )
            )
            LLMUsageEventRepository(db).create(
                LLMUsageEventCreate(
                    pipeline_run_id=pipeline_run_id,
                    transcript_id=transcript["id"],
                    agent_name="SignalExtractionAgent",
                    pipeline_step="segment_signal_extraction",
                    model="gpt-5.4",
                    prompt_version="signal_extraction_v1",
                    pricing_version="2026-05-20",
                    retry_count=2,
                    status="failed",
                    error_type="RateLimitError",
                    created_at=datetime(2026, 5, 20, 0, 1, tzinfo=UTC),
                )
            )
            db.commit()

        list_response = client.get("/transcripts", headers=headers)
        assert list_response.status_code == 200
        transcript_list_row = list_response.json()[0]
        assert transcript_list_row["driver_count"] == 1
        assert transcript_list_row["usage"]["calls"] == 2
        assert transcript_list_row["usage"]["input_tokens"] == 100
        assert transcript_list_row["usage"]["retry_count"] == 3
        assert "raw_text" not in transcript_list_row["usage"]
        assert "prompt_payload" not in transcript_list_row["usage"]

        detail_response = client.get(f"/transcripts/{transcript['id']}", headers=headers)
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["turns"][0]["speaker_role"] == "advisor"
        assert detail["final_signals"][0]["item_type"] == "driver"
        assert detail["usage"]["estimated_total_cost_usd"] == 0.012

        turns_response = client.get(f"/transcripts/{transcript['id']}/turns", headers=headers)
        assert turns_response.status_code == 200
        assert turns_response.json()[0]["source_chunk_id"].endswith("_chunk_001")

        signals_response = client.get(f"/signals?transcript_id={transcript['id']}", headers=headers)
        assert signals_response.status_code == 200
        assert signals_response.json()[0]["advisor_quote"] == "I need stronger support."

        runs_response = client.get("/pipeline-runs", headers=headers)
        assert runs_response.status_code == 200
        run_list_row = runs_response.json()[0]
        assert run_list_row["id"] == pipeline_run_id
        assert run_list_row["usage"]["calls"] == 2
        assert run_list_row["usage_by_step"][0]["pipeline_step"] == "segment_signal_extraction"
        assert run_list_row["usage_by_step"][0]["models"] == ["gpt-5.4"]

        run_response = client.get(f"/pipeline-runs/{pipeline_run_id}", headers=headers)
        assert run_response.status_code == 200
        run_detail = run_response.json()
        assert run_detail["transcript_id"] == transcript["id"]
        assert run_detail["usage"]["output_tokens"] == 20
        assert "raw_text" not in run_detail["usage"]
        assert "prompt_payload" not in run_detail["usage"]
    finally:
        app.dependency_overrides.clear()


def test_usage_responses_zero_fill_when_no_events(
    db_session_factory: sessionmaker[Session],
) -> None:
    def override_get_db() -> Iterator[Session]:
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with db_session_factory() as db:
            from app.db.repositories.transcript_repo import TranscriptRepository

            transcript = TranscriptRepository(db).create(
                title="Sanitized empty usage call",
                raw_text="sanitized transcript",
            )
            run = PipelineRunRepository(db).create(transcript_id=transcript.id)
            run_id = run.id
            db.commit()

        client = TestClient(app)
        headers = auth_headers()
        transcript_row = client.get("/transcripts", headers=headers).json()[0]
        assert transcript_row["usage"] == {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_total_cost_usd": 0.0,
            "retry_count": 0,
            "latest_pricing_version": None,
        }

        run_row = client.get(f"/pipeline-runs/{run_id}", headers=headers).json()
        assert run_row["usage"]["calls"] == 0
        assert run_row["usage_by_step"] == []
    finally:
        app.dependency_overrides.clear()
