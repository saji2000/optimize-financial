from email import policy
from email.parser import BytesParser
from pathlib import PurePath

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain.transcript_schema import (
    TranscriptCreate,
    TranscriptDetailRead,
    TranscriptRead,
    TranscriptSummaryRead,
    TranscriptTurnRead,
)
from app.services.pipeline_service import queue_pipeline_run
from app.services.transcript_service import (
    create_transcript_with_run,
    get_transcript_detail,
    list_transcript_turns,
    list_transcripts,
)

router = APIRouter()


@router.post("", response_model=TranscriptRead, status_code=status.HTTP_202_ACCEPTED)
async def create_transcript(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TranscriptRead:
    payload = await _transcript_upload_payload(request)
    transcript, pipeline_run_id = create_transcript_with_run(payload, db)
    background_tasks.add_task(queue_pipeline_run, transcript.id, pipeline_run_id)
    return transcript


@router.get("", response_model=list[TranscriptSummaryRead])
def list_transcript_rows(db: Session = Depends(get_db)) -> list[TranscriptSummaryRead]:
    return list_transcripts(db)


@router.get("/{transcript_id}", response_model=TranscriptDetailRead)
def get_transcript(
    transcript_id: str,
    db: Session = Depends(get_db),
) -> TranscriptDetailRead:
    return get_transcript_detail(transcript_id, db)


@router.get("/{transcript_id}/turns", response_model=list[TranscriptTurnRead])
def get_transcript_turns(
    transcript_id: str,
    db: Session = Depends(get_db),
) -> list[TranscriptTurnRead]:
    return list_transcript_turns(transcript_id, db)


async def _transcript_upload_payload(request: Request) -> TranscriptCreate:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Expected multipart/form-data upload",
        )

    body = await request.body()
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
        + body
    )
    if not message.is_multipart():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload")

    file_bytes: bytes | None = None
    filename: str | None = None
    title: str | None = None
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if name == "file":
            filename = part.get_filename()
            file_bytes = part.get_payload(decode=True) or b""
        elif name == "title":
            raw_title = part.get_payload(decode=True) or b""
            title = raw_title.decode("utf-8", errors="replace").strip() or None

    if file_bytes is None or not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing .txt file")
    if not filename.casefold().endswith(".txt"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .txt files are supported")

    try:
        raw_text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript file must be UTF-8 text",
        ) from exc
    if not raw_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transcript file is empty")

    transcript_title = title or PurePath(filename).stem
    return TranscriptCreate(title=transcript_title, raw_text=raw_text)
