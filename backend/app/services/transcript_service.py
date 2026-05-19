from app.domain.transcript_schema import TranscriptCreate, TranscriptRead


def create_transcript(payload: TranscriptCreate) -> TranscriptRead:
    return TranscriptRead(id="pending", title=payload.title, status="queued")

