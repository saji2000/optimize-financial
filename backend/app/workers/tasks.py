from app.pipeline.orchestrator import PipelineOrchestrator
from app.workers.celery_app import celery_app


def enqueue_transcript_pipeline(transcript_id: str) -> None:
    run_transcript_pipeline.delay(transcript_id)


@celery_app.task(name="run_transcript_pipeline")
def run_transcript_pipeline(transcript_id: str) -> dict[str, str]:
    orchestrator = PipelineOrchestrator()
    orchestrator.run(transcript_id)
    return {"status": "completed", "transcript_id": transcript_id}

