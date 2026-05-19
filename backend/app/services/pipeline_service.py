from app.workers.tasks import enqueue_transcript_pipeline


def queue_pipeline_run(transcript_id: str) -> None:
    enqueue_transcript_pipeline(transcript_id)

