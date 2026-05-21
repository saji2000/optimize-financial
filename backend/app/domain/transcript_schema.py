from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.signal_schema import SignalRead


class TranscriptCreate(BaseModel):
    title: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)


class TranscriptRead(BaseModel):
    id: str
    title: str
    status: str


class TranscriptSummaryRead(TranscriptRead):
    created_at: datetime
    driver_count: int = 0
    blocker_count: int = 0


class TranscriptTurnRead(BaseModel):
    id: str
    transcript_id: str
    sequence: int
    timestamp: str | None = None
    end_timestamp: str | None = None
    speaker: str
    speaker_role: str
    text: str
    source_chunk_id: str


class TranscriptDetailRead(TranscriptSummaryRead):
    updated_at: datetime
    error_type: str | None = None
    error_message: str | None = None
    turns: list[TranscriptTurnRead] = Field(default_factory=list)
    final_signals: list[SignalRead] = Field(default_factory=list)
