from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models.final_signal import FinalSignal
from app.db.models.signal import Signal


class SignalRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_finalized(self) -> list[Signal]:
        return list(self.db.query(Signal).filter(Signal.status == "approved").all())

    def replace_final_signals(self, transcript_id: str, signals: list[FinalSignal]) -> None:
        self.db.query(FinalSignal).filter(
            FinalSignal.transcript_id == transcript_id
        ).delete(synchronize_session=False)
        self.db.add_all(signals)
        self.db.flush()

    def list_final_signals(self, transcript_id: str | None = None) -> list[FinalSignal]:
        query = self.db.query(FinalSignal)
        if transcript_id is not None:
            query = query.filter(FinalSignal.transcript_id == transcript_id)
        return list(
            query.order_by(
                FinalSignal.transcript_id.asc(),
                FinalSignal.item_type.asc(),
                FinalSignal.rank.asc(),
            ).all()
        )

    def get_final_signal(self, signal_id: str) -> FinalSignal | None:
        return self.db.get(FinalSignal, signal_id)

    def get_final_signals_by_ids(self, signal_ids: list[str]) -> list[FinalSignal]:
        if not signal_ids:
            return []
        return list(
            self.db.query(FinalSignal).filter(FinalSignal.id.in_(signal_ids)).all()
        )

    def update_feedback(
        self,
        signal: FinalSignal,
        *,
        review_status: str | None = None,
        flag: bool | None = None,
        reviewer_notes: str | None = None,
        reviewed_by: str | None = None,
    ) -> FinalSignal:
        if review_status is not None:
            signal.review_status = review_status
        if flag is not None:
            signal.flag = flag
        if reviewer_notes is not None:
            signal.reviewer_notes = reviewer_notes
        signal.reviewed_by = reviewed_by
        signal.reviewed_at = datetime.now(UTC)
        self.db.flush()
        return signal
