from pydantic import BaseModel

from app.domain.enums import PipelineStatus


class PipelineRunRead(BaseModel):
    id: str
    transcript_id: str
    status: PipelineStatus

