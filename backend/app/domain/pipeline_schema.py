from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import PipelineStatus


class PipelineRunRead(BaseModel):
    id: str
    transcript_id: str
    status: PipelineStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    error_type: str | None = None
    error_message: str | None = None
