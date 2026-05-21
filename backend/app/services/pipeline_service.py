from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.pipeline_run import PipelineRun
from app.db.repositories.llm_usage_repo import LLMUsageEventRepository
from app.db.repositories.pipeline_run_repo import PipelineRunRepository
from app.domain.pipeline_schema import PipelineRunRead
from app.services.llm_usage_service import summarize_usage, summarize_usage_by_step
from app.workers.tasks import enqueue_transcript_pipeline


def queue_pipeline_run(transcript_id: str, pipeline_run_id: str | None = None) -> None:
    enqueue_transcript_pipeline(transcript_id, pipeline_run_id=pipeline_run_id)


def list_pipeline_runs(db: Session) -> list[PipelineRunRead]:
    usage_repo = LLMUsageEventRepository(db)
    return [
        pipeline_run_to_read(
            run,
            usage_events=usage_repo.list_by_pipeline_run(run.id),
        )
        for run in PipelineRunRepository(db).list()
    ]


def get_pipeline_run(pipeline_run_id: str, db: Session) -> PipelineRunRead:
    run = PipelineRunRepository(db).get(pipeline_run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found")
    return pipeline_run_to_read(
        run,
        usage_events=LLMUsageEventRepository(db).list_by_pipeline_run(run.id),
    )


def pipeline_run_to_read(run: PipelineRun, usage_events=None) -> PipelineRunRead:
    usage_events = usage_events or []
    return PipelineRunRead(
        id=run.id,
        transcript_id=run.transcript_id,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        error_type=run.error_type,
        error_message=run.error_message,
        usage=summarize_usage(usage_events),
        usage_by_step=summarize_usage_by_step(usage_events),
    )
