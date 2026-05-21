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
