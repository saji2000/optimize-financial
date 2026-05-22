import logging

from app.core.sentry import capture_sanitized_exception
from app.db.repositories.pipeline_run_repo import PipelineRunRepository
from app.db.repositories.transcript_repo import TranscriptRepository
from app.db.session import SessionLocal
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.persistence import persist_pipeline_outputs
from app.workers.celery_app import celery_app


LOGGER = logging.getLogger(__name__)


def enqueue_transcript_pipeline(
    transcript_id: str,
    pipeline_run_id: str | None = None,
) -> None:
    run_transcript_pipeline.delay(transcript_id, pipeline_run_id)


@celery_app.task(name="run_transcript_pipeline")
def run_transcript_pipeline(
    transcript_id: str,
    pipeline_run_id: str | None = None,
) -> dict[str, str]:
    run_id, raw_text = _mark_started(transcript_id, pipeline_run_id)
    try:
        outputs = PipelineOrchestrator(pipeline_run_id=run_id).run_outputs(
            transcript_id=transcript_id,
            raw_text=raw_text,
        )
        with SessionLocal() as db:
            transcript_repo = TranscriptRepository(db)
            run_repo = PipelineRunRepository(db)
            transcript = transcript_repo.get(transcript_id)
            run = run_repo.get(run_id)
            if transcript is None or run is None:
                raise RuntimeError("Pipeline persistence target disappeared")

            persist_pipeline_outputs(
                db,
                prepared_transcript=outputs.prepared_transcript,
                final_signals=outputs.final_signals,
            )
            transcript_repo.update_status(transcript, status="completed")
            run_repo.mark_completed(run)
            db.commit()
    except Exception as exc:
        error_type, error_message = sanitized_error_metadata(exc)
        _mark_failed(
            transcript_id=transcript_id,
            pipeline_run_id=run_id,
            error_type=error_type,
            error_message=error_message,
        )
        capture_sanitized_exception(
            exc,
            pipeline_run_id=run_id,
            transcript_id=transcript_id,
            agent_name="PipelineOrchestrator",
            pipeline_step="worker_task",
        )
        LOGGER.error(
            "Pipeline task failed for transcript_id=%r pipeline_run_id=%r error_type=%s",
            transcript_id,
            run_id,
            error_type,
        )
        raise

    return {"status": "completed", "transcript_id": transcript_id, "pipeline_run_id": run_id}


def _mark_started(transcript_id: str, pipeline_run_id: str | None) -> tuple[str, str]:
    with SessionLocal() as db:
        transcript_repo = TranscriptRepository(db)
        run_repo = PipelineRunRepository(db)
        transcript = transcript_repo.get(transcript_id)
        if transcript is None:
            raise ValueError("Transcript not found")

        run = run_repo.get(pipeline_run_id) if pipeline_run_id is not None else None
        if run is None:
            run = run_repo.create(transcript_id=transcript_id, status="queued")

        raw_text = transcript.raw_text
        transcript_repo.update_status(transcript, status="running")
        run_repo.mark_running(run)
        db.commit()
        return run.id, raw_text


def _mark_failed(
    *,
    transcript_id: str,
    pipeline_run_id: str,
    error_type: str,
    error_message: str,
) -> None:
    with SessionLocal() as db:
        transcript_repo = TranscriptRepository(db)
        run_repo = PipelineRunRepository(db)
        transcript = transcript_repo.get(transcript_id)
        run = run_repo.get(pipeline_run_id)
        if transcript is not None:
            transcript_repo.update_status(
                transcript,
                status="failed",
                error_type=error_type,
                error_message=error_message,
            )
        if run is not None:
            run_repo.mark_failed(
                run,
                error_type=error_type,
                error_message=error_message,
            )
        db.commit()


def sanitized_error_metadata(error: Exception) -> tuple[str, str]:
    error_type = error.__class__.__name__
    return error_type, f"Pipeline failed with {error_type}."
