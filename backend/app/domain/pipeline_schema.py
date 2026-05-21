from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import PipelineStatus
from app.domain.usage_schema import LLMUsageStepRead, LLMUsageSummaryRead


class PipelineRunRead(BaseModel):
    id: str
    transcript_id: str
    status: PipelineStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    error_type: str | None = None
    error_message: str | None = None
    usage: LLMUsageSummaryRead = Field(default_factory=LLMUsageSummaryRead)
    usage_by_step: list[LLMUsageStepRead] = Field(default_factory=list)
