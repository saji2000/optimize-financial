from sqlalchemy.orm import Session, sessionmaker

from app.db.repositories.pipeline_run_repo import PipelineRunRepository
from app.db.repositories.signal_repo import SignalRepository
from app.db.repositories.transcript_repo import TranscriptRepository
from app.pipeline.persistence import persist_pipeline_outputs
from app.pipeline.schemas import FinalSignal, PreparedTranscript, TranscriptChunk, TranscriptTurn


def test_repositories_create_transcript_and_persist_pipeline_outputs(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as db:
        transcript_repo = TranscriptRepository(db)
        run_repo = PipelineRunRepository(db)
        transcript = transcript_repo.create(
            title="Sanitized recruiting call",
            raw_text="00:01:00 Advisor: I need stronger support.",
        )
        run = run_repo.create(transcript_id=transcript.id)
        run_repo.mark_running(run)
        prepared = PreparedTranscript(
            transcript_id=transcript.id,
            chunks=[
                TranscriptChunk(
                    transcript_id=transcript.id,
                    chunk_id=f"{transcript.id}_chunk_001",
                    turns=[
                        TranscriptTurn(
                            sequence=1,
                            timestamp="00:01:00",
                            end_timestamp="00:01:05",
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
                transcript_id=transcript.id,
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
        transcript_repo.update_status(transcript, status="completed")
        run_repo.mark_completed(run)
        db.commit()

        turns = transcript_repo.list_turns(transcript.id)
        signals = SignalRepository(db).list_final_signals(transcript_id=transcript.id)
        assert [turn.sequence for turn in turns] == [1]
        assert turns[0].source_chunk_id == f"{transcript.id}_chunk_001"
        assert signals[0].item_type == "driver"
        assert signals[0].advisor_quote == "I need stronger support."
        assert transcript.status == "completed"
        assert run.status == "completed"
