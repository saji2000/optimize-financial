from sqlalchemy.orm import Session

from app.db.models.llm_usage_event import LLMUsageEvent
from app.services.llm_usage_service import LLMUsageEventCreate


class LLMUsageEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, event: LLMUsageEventCreate) -> LLMUsageEvent:
        row = LLMUsageEvent(**event.model_dump())
        self.db.add(row)
        self.db.flush()
        return row

    def list_by_pipeline_run(self, pipeline_run_id: str) -> list[LLMUsageEvent]:
        return list(
            self.db.query(LLMUsageEvent)
            .filter(LLMUsageEvent.pipeline_run_id == pipeline_run_id)
            .order_by(LLMUsageEvent.created_at.asc())
            .all()
        )

    def list_by_transcript(self, transcript_id: str) -> list[LLMUsageEvent]:
        return list(
            self.db.query(LLMUsageEvent)
            .filter(LLMUsageEvent.transcript_id == transcript_id)
            .order_by(LLMUsageEvent.created_at.asc())
            .all()
        )
