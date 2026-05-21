from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.db.repositories.pipeline_run_repo import PipelineRunRepository
from app.main import app
from app.pipeline.persistence import persist_pipeline_outputs
from app.pipeline.schemas import FinalSignal, PreparedTranscript, TranscriptChunk, TranscriptTurn


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
        response = client.post(
            "/transcripts",
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
            db.commit()
            pipeline_run_id = PipelineRunRepository(db).list()[0].id

        list_response = client.get("/transcripts")
        assert list_response.status_code == 200
        assert list_response.json()[0]["driver_count"] == 1

        detail_response = client.get(f"/transcripts/{transcript['id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["turns"][0]["speaker_role"] == "advisor"
        assert detail["final_signals"][0]["item_type"] == "driver"

        turns_response = client.get(f"/transcripts/{transcript['id']}/turns")
        assert turns_response.status_code == 200
        assert turns_response.json()[0]["source_chunk_id"].endswith("_chunk_001")

        signals_response = client.get(f"/signals?transcript_id={transcript['id']}")
        assert signals_response.status_code == 200
        assert signals_response.json()[0]["advisor_quote"] == "I need stronger support."

        runs_response = client.get("/pipeline-runs")
        assert runs_response.status_code == 200
        assert runs_response.json()[0]["id"] == pipeline_run_id

        run_response = client.get(f"/pipeline-runs/{pipeline_run_id}")
        assert run_response.status_code == 200
        assert run_response.json()["transcript_id"] == transcript["id"]
    finally:
        app.dependency_overrides.clear()
