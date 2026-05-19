from sqlalchemy.orm import Session

from app.db.models.pipeline_run import PipelineRun


class PipelineRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[PipelineRun]:
        return list(self.db.query(PipelineRun).all())

