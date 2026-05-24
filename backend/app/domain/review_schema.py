from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import ReviewStatus


class SignalFeedbackUpdate(BaseModel):
    review_status: ReviewStatus | None = None
    flag: bool | None = None
    reviewer_notes: str | None = None


class BulkFeedbackUpdate(BaseModel):
    signal_ids: list[str]
    review_status: ReviewStatus | None = None
    flag: bool | None = None
    reviewer_notes: str | None = None


class SignalFeedbackResponse(BaseModel):
    signal_id: str
    review_status: ReviewStatus
    flag: bool
    reviewer_notes: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None


class BulkFeedbackResponse(BaseModel):
    updated: list[SignalFeedbackResponse]
    not_found: list[str]

