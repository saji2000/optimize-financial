from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.transcript import Transcript
from app.db.models.transcript_turn import TranscriptTurn
from app.db.repositories.pipeline_run_repo import PipelineRunRepository
from app.db.repositories.signal_repo import SignalRepository
from app.db.repositories.transcript_repo import TranscriptRepository
from app.domain.transcript_schema import (
    TranscriptCreate,
    TranscriptDetailRead,
    TranscriptRead,
    TranscriptSummaryRead,
    TranscriptTurnRead,
)
from app.services.signal_service import final_signal_to_read


def create_transcript(payload: TranscriptCreate, db: Session) -> TranscriptRead:
    transcript, _pipeline_run_id = create_transcript_with_run(payload, db)
    return transcript


def create_transcript_with_run(
    payload: TranscriptCreate,
    db: Session,
) -> tuple[TranscriptRead, str]:
    transcript_repo = TranscriptRepository(db)
    run_repo = PipelineRunRepository(db)
    transcript = transcript_repo.create(
        title=payload.title,
        raw_text=payload.raw_text,
        status="queued",
    )
    pipeline_run = run_repo.create(transcript_id=transcript.id, status="queued")
    db.commit()
    db.refresh(transcript)
    db.refresh(pipeline_run)
    return transcript_to_read(transcript), pipeline_run.id


def list_transcripts(db: Session) -> list[TranscriptSummaryRead]:
    transcript_repo = TranscriptRepository(db)
    counts = transcript_repo.signal_counts()
    return [
        transcript_to_summary(transcript, counts.get(transcript.id, {}))
        for transcript in transcript_repo.list()
    ]


def get_transcript_detail(transcript_id: str, db: Session) -> TranscriptDetailRead:
    transcript_repo = TranscriptRepository(db)
    transcript = transcript_repo.get(transcript_id)
    if transcript is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")

    counts = transcript_repo.signal_counts().get(transcript.id, {})
    turns = [turn_to_read(turn) for turn in transcript_repo.list_turns(transcript.id)]
    signals = [
        final_signal_to_read(signal)
        for signal in SignalRepository(db).list_final_signals(transcript_id=transcript.id)
    ]
    summary = transcript_to_summary(transcript, counts)
    return TranscriptDetailRead(
        **summary.model_dump(),
        updated_at=transcript.updated_at,
        error_type=transcript.error_type,
        error_message=transcript.error_message,
        turns=turns,
        final_signals=signals,
    )


def list_transcript_turns(transcript_id: str, db: Session) -> list[TranscriptTurnRead]:
    transcript_repo = TranscriptRepository(db)
    if transcript_repo.get(transcript_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    return [turn_to_read(turn) for turn in transcript_repo.list_turns(transcript_id)]


def transcript_to_read(transcript: Transcript) -> TranscriptRead:
    return TranscriptRead(
        id=transcript.id,
        title=transcript.title,
        status=transcript.status,
    )


def transcript_to_summary(
    transcript: Transcript,
    counts: dict[str, int] | None = None,
) -> TranscriptSummaryRead:
    counts = counts or {}
    return TranscriptSummaryRead(
        id=transcript.id,
        title=transcript.title,
        status=transcript.status,
        created_at=transcript.created_at,
        driver_count=counts.get("driver", 0),
        blocker_count=counts.get("blocker", 0),
    )


def turn_to_read(turn: TranscriptTurn) -> TranscriptTurnRead:
    return TranscriptTurnRead(
        id=turn.id,
        transcript_id=turn.transcript_id,
        sequence=turn.sequence,
        timestamp=turn.timestamp,
        end_timestamp=turn.end_timestamp,
        speaker=turn.speaker,
        speaker_role=turn.speaker_role,
        text=turn.text,
        source_chunk_id=turn.source_chunk_id,
    )
