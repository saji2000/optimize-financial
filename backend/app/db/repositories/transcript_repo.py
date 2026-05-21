from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.transcript import Transcript
from app.db.models.transcript_turn import TranscriptTurn


class TranscriptRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        title: str,
        raw_text: str,
        status: str = "queued",
        transcript_id: str | None = None,
    ) -> Transcript:
        transcript = Transcript(
            id=transcript_id,
            title=title,
            raw_text=raw_text,
            status=status,
        )
        if transcript_id is None:
            transcript = Transcript(title=title, raw_text=raw_text, status=status)
        self.db.add(transcript)
        self.db.flush()
        return transcript

    def get(self, transcript_id: str) -> Transcript | None:
        return self.db.get(Transcript, transcript_id)

    def list(self) -> list[Transcript]:
        return list(self.db.query(Transcript).order_by(Transcript.created_at.desc()).all())

    def signal_counts(self) -> dict[str, dict[str, int]]:
        from app.db.models.final_signal import FinalSignal

        rows = (
            self.db.query(
                FinalSignal.transcript_id,
                FinalSignal.item_type,
                func.count(FinalSignal.id),
            )
            .group_by(FinalSignal.transcript_id, FinalSignal.item_type)
            .all()
        )
        counts: dict[str, dict[str, int]] = {}
        for transcript_id, item_type, count in rows:
            counts.setdefault(transcript_id, {"driver": 0, "blocker": 0})
            counts[transcript_id][item_type] = int(count)
        return counts

    def update_status(
        self,
        transcript: Transcript,
        *,
        status: str,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> Transcript:
        transcript.status = status
        transcript.updated_at = datetime.now(UTC)
        transcript.error_type = error_type
        transcript.error_message = error_message
        self.db.flush()
        return transcript

    def replace_turns(self, transcript_id: str, turns: list[TranscriptTurn]) -> None:
        self.db.query(TranscriptTurn).filter(
            TranscriptTurn.transcript_id == transcript_id
        ).delete(synchronize_session=False)
        self.db.add_all(turns)
        self.db.flush()

    def list_turns(self, transcript_id: str) -> list[TranscriptTurn]:
        return list(
            self.db.query(TranscriptTurn)
            .filter(TranscriptTurn.transcript_id == transcript_id)
            .order_by(TranscriptTurn.sequence.asc())
            .all()
        )
