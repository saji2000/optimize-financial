from fastapi import APIRouter, BackgroundTasks, status

from app.domain.transcript_schema import TranscriptCreate, TranscriptRead
from app.workers.tasks import enqueue_transcript_pipeline

router = APIRouter()


@router.post("", response_model=TranscriptRead, status_code=status.HTTP_202_ACCEPTED)
def create_transcript(payload: TranscriptCreate, background_tasks: BackgroundTasks) -> TranscriptRead:
    transcript = TranscriptRead(id="pending", title=payload.title, status="queued")
    background_tasks.add_task(enqueue_transcript_pipeline, transcript.id)
    return transcript


@router.get("", response_model=list[TranscriptRead])
def list_transcripts() -> list[TranscriptRead]:
    return []

