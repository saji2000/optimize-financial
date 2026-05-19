from sqlalchemy.orm import Session

from app.db.models.transcript import Transcript


class TranscriptRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Transcript]:
        return list(self.db.query(Transcript).all())

