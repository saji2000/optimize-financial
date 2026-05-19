from pydantic import BaseModel


class ReviewDecision(BaseModel):
    signal_id: str
    decision: str
    reviewer_id: str | None = None
    notes: str | None = None

