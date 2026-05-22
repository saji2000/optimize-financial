import json
import shutil
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.db.repositories.signal_repo import SignalRepository
from app.db.repositories.transcript_repo import TranscriptRepository
from scripts.import_agent_artifacts import import_agent_artifacts


def test_import_agent_artifacts_imports_final_signals_and_matching_turns(
    db_session_factory: sessionmaker[Session],
) -> None:
    temp_dir = Path(__file__).resolve().parents[1] / ".test-tmp" / f"artifacts-{uuid4()}"
    base_path = temp_dir / "agents-outputs"
    (base_path / "final-formatter").mkdir(parents=True)
    (base_path / "transcript-preparation").mkdir(parents=True)
    final_envelope = {
        "transcript_id": "call_001",
        "agent_name": "FinalFormatter",
        "pipeline_step": "final_formatting",
        "created_at": "2026-05-20T12:00:00Z",
        "output_schema": "FinalSignal[]",
        "output": [
            {
                "transcript_id": "call_001",
                "item_type": "driver",
                "rank": 1,
                "category": "Operational support",
                "advisor_quote": "I need stronger support.",
                "timestamp": "00:01:00",
                "evidence_strength": "explicit",
                "rationale": "The advisor states a support need.",
            }
        ],
    }
    prepared_envelope = {
        "transcript_id": "call_001",
        "agent_name": "TranscriptPreparationAgent",
        "pipeline_step": "transcript_preparation",
        "created_at": "2026-05-20T12:00:00Z",
        "output_schema": "PreparedTranscript",
        "output": {
            "transcript_id": "call_001",
            "metadata": None,
            "chunks": [
                {
                    "transcript_id": "call_001",
                    "chunk_id": "call_001_chunk_001",
                    "start_timestamp": "00:01:00",
                    "end_timestamp": "00:01:05",
                    "turns": [
                        {
                            "sequence": 1,
                            "timestamp": "00:01:00",
                            "end_timestamp": "00:01:05",
                            "speaker": "Advisor",
                            "speaker_role": "advisor",
                            "text": "I need stronger support.",
                        }
                    ],
                }
            ],
        },
    }
    (base_path / "final-formatter" / "call_001.json").write_text(
        json.dumps(final_envelope),
        encoding="utf-8",
    )
    (base_path / "transcript-preparation" / "call_001.json").write_text(
        json.dumps(prepared_envelope),
        encoding="utf-8",
    )

    try:
        counts = import_agent_artifacts(base_path, session_factory=db_session_factory)

        assert counts == {"artifacts": 1, "signals": 1, "turns": 1}
        with db_session_factory() as db:
            transcript = TranscriptRepository(db).get("call_001")
            assert transcript is not None
            assert transcript.status == "completed"
            assert len(TranscriptRepository(db).list_turns("call_001")) == 1
            assert len(SignalRepository(db).list_final_signals("call_001")) == 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
