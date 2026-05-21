from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.pipeline_run import PipelineRun
from app.db.repositories.pipeline_run_repo import PipelineRunRepository
from app.domain.pipeline_schema import PipelineRunRead
from app.workers.tasks import enqueue_transcript_pipeline


def queue_pipeline_run(transcript_id: str, pipeline_run_id: str | None = None) -> None:
    enqueue_transcript_pipeline(transcript_id, pipeline_run_id=pipeline_run_id)


def list_pipeline_runs(db: Session) -> list[PipelineRunRead]:
    return [pipeline_run_to_read(run) for run in PipelineRunRepository(db).list()]


def get_pipeline_run(pipeline_run_id: str, db: Session) -> PipelineRunRead:
    run = PipelineRunRepository(db).get(pipeline_run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found")
    return pipeline_run_to_read(run)


def pipeline_run_to_read(run: PipelineRun) -> PipelineRunRead:
    return PipelineRunRead(
        id=run.id,
        transcript_id=run.transcript_id,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        error_type=run.error_type,
        error_message=run.error_message,
    )
