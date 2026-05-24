from sqlalchemy.orm import Session

from app.db.models.final_signal import FinalSignal
from app.db.repositories.signal_repo import SignalRepository
from app.domain.signal_schema import SignalRead


def list_representative_signals(
    db: Session,
    transcript_id: str | None = None,
) -> list[SignalRead]:
    return [
        final_signal_to_read(signal)
        for signal in SignalRepository(db).list_final_signals(transcript_id=transcript_id)
    ]


def final_signal_to_read(signal: FinalSignal) -> SignalRead:
    return SignalRead(
        id=signal.id,
        transcript_id=signal.transcript_id,
        item_type=signal.item_type,
        rank=signal.rank,
        category=signal.category,
        advisor_quote=signal.advisor_quote,
        timestamp=signal.timestamp,
        evidence_strength=signal.evidence_strength,
        rationale=signal.rationale,
        review_status=signal.review_status,
        flag=signal.flag,
        reviewer_notes=signal.reviewer_notes,
        reviewed_at=signal.reviewed_at,
        reviewed_by=signal.reviewed_by,
    )
