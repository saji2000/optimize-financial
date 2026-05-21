from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models.pipeline_run import PipelineRun


class PipelineRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        transcript_id: str,
        status: str = "queued",
        pipeline_run_id: str | None = None,
    ) -> PipelineRun:
        run = PipelineRun(
            id=pipeline_run_id,
            transcript_id=transcript_id,
            status=status,
        )
        if pipeline_run_id is None:
            run = PipelineRun(transcript_id=transcript_id, status=status)
        self.db.add(run)
        self.db.flush()
        return run

    def get(self, pipeline_run_id: str) -> PipelineRun | None:
        return self.db.get(PipelineRun, pipeline_run_id)

    def list(self) -> list[PipelineRun]:
        return list(self.db.query(PipelineRun).order_by(PipelineRun.created_at.desc()).all())

    def mark_running(self, run: PipelineRun) -> PipelineRun:
        run.status = "running"
        run.started_at = datetime.now(UTC)
        run.completed_at = None
        run.error_type = None
        run.error_message = None
        self.db.flush()
        return run

    def mark_completed(self, run: PipelineRun) -> PipelineRun:
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        run.error_type = None
        run.error_message = None
        self.db.flush()
        return run

    def mark_failed(
        self,
        run: PipelineRun,
        *,
        error_type: str,
        error_message: str,
    ) -> PipelineRun:
        run.status = "failed"
        run.completed_at = datetime.now(UTC)
        run.error_type = error_type
        run.error_message = error_message
        self.db.flush()
        return run
