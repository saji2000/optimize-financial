from sqlalchemy.orm import Session

from app.db.models.signal import Signal


class SignalRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_finalized(self) -> list[Signal]:
        return list(self.db.query(Signal).filter(Signal.status == "approved").all())

