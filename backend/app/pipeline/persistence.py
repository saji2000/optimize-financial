from sqlalchemy.orm import Session

from app.db.models.final_signal import FinalSignal as FinalSignalRow
from app.db.models.transcript_turn import TranscriptTurn as TranscriptTurnRow
from app.db.repositories.signal_repo import SignalRepository
from app.db.repositories.transcript_repo import TranscriptRepository
from app.pipeline.schemas import FinalSignal, PreparedTranscript, TranscriptTurn


def persist_pipeline_outputs(
    db: Session,
    *,
    prepared_transcript: PreparedTranscript,
    final_signals: list[FinalSignal],
) -> None:
    transcript_id = prepared_transcript.transcript_id
    TranscriptRepository(db).replace_turns(
        transcript_id,
        prepared_turn_rows(prepared_transcript),
    )
    SignalRepository(db).replace_final_signals(
        transcript_id,
        final_signal_rows(final_signals),
    )


def prepared_turn_rows(prepared_transcript: PreparedTranscript) -> list[TranscriptTurnRow]:
    rows: list[TranscriptTurnRow] = []
    seen_sequences: set[int] = set()
    for chunk in prepared_transcript.chunks:
        for turn in chunk.turns:
            if turn.sequence in seen_sequences:
                continue
            seen_sequences.add(turn.sequence)
            rows.append(
                turn_row(
                    transcript_id=prepared_transcript.transcript_id,
                    source_chunk_id=chunk.chunk_id,
                    turn=turn,
                )
            )
    rows.sort(key=lambda row: row.sequence)
    return rows


def turn_row(
    *,
    transcript_id: str,
    source_chunk_id: str,
    turn: TranscriptTurn,
) -> TranscriptTurnRow:
    return TranscriptTurnRow(
        transcript_id=transcript_id,
        sequence=turn.sequence,
        timestamp=turn.timestamp,
        end_timestamp=turn.end_timestamp,
        speaker=turn.speaker,
        speaker_role=turn.speaker_role,
        text=turn.text,
        source_chunk_id=source_chunk_id,
    )


def final_signal_rows(final_signals: list[FinalSignal]) -> list[FinalSignalRow]:
    return [
        FinalSignalRow(
            transcript_id=signal.transcript_id,
            item_type=signal.item_type.value,
            rank=signal.rank,
            category=signal.category,
            advisor_quote=signal.advisor_quote,
            timestamp=signal.timestamp,
            evidence_strength=signal.evidence_strength.value,
            rationale=signal.rationale,
        )
        for signal in final_signals
    ]
