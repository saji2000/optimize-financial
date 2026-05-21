import argparse
import json
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from app.db.repositories.signal_repo import SignalRepository
from app.db.repositories.transcript_repo import TranscriptRepository
from app.db.session import SessionLocal
from app.pipeline.agent_output_writer import DEFAULT_AGENT_OUTPUT_BASE_PATH, sanitize_transcript_id
from app.pipeline.persistence import final_signal_rows, persist_pipeline_outputs, prepared_turn_rows
from app.pipeline.schemas import FinalSignal, PreparedTranscript


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import final formatter artifacts into the V1 database tables.",
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=DEFAULT_AGENT_OUTPUT_BASE_PATH,
        help="Path containing agents-outputs subfolders.",
    )
    args = parser.parse_args()
    imported = import_agent_artifacts(args.base_path)
    print(
        "Imported "
        f"{imported['artifacts']} artifact(s), "
        f"{imported['signals']} final signal(s), "
        f"{imported['turns']} prepared turn(s)."
    )


def import_agent_artifacts(
    base_path: Path,
    session_factory: sessionmaker = SessionLocal,
) -> dict[str, int]:
    final_formatter_path = base_path / "final-formatter"
    final_paths = sorted(final_formatter_path.glob("*.json")) if final_formatter_path.exists() else []
    counts = {"artifacts": 0, "signals": 0, "turns": 0}

    with session_factory() as db:
        transcript_repo = TranscriptRepository(db)
        signal_repo = SignalRepository(db)
        for final_path in final_paths:
            final_envelope = _read_json(final_path)
            transcript_id = str(final_envelope["transcript_id"])
            final_signals = [
                FinalSignal.model_validate(item) for item in final_envelope.get("output", [])
            ]
            transcript = transcript_repo.get(transcript_id)
            if transcript is None:
                transcript = transcript_repo.create(
                    transcript_id=transcript_id,
                    title=transcript_id,
                    raw_text="",
                    status="completed",
                )
            else:
                transcript_repo.update_status(transcript, status="completed")

            prepared = _matching_prepared_transcript(base_path, transcript_id)
            if prepared is None:
                signal_repo.replace_final_signals(transcript_id, final_signal_rows(final_signals))
            else:
                persist_pipeline_outputs(
                    db,
                    prepared_transcript=prepared,
                    final_signals=final_signals,
                )
                counts["turns"] += len(prepared_turn_rows(prepared))

            counts["artifacts"] += 1
            counts["signals"] += len(final_signals)
        db.commit()

    return counts


def _matching_prepared_transcript(
    base_path: Path,
    transcript_id: str,
) -> PreparedTranscript | None:
    path = base_path / "transcript-preparation" / f"{sanitize_transcript_id(transcript_id)}.json"
    if not path.exists():
        return None
    envelope = _read_json(path)
    return PreparedTranscript.model_validate(envelope["output"])


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
