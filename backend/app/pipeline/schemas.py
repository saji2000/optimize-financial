from pydantic import BaseModel, Field

from app.domain.enums import EvidenceStrength, SignalType


class TranscriptMetadata(BaseModel):
    meeting_id: str | None = None
    meeting_topic: str | None = None
    host_email: str | None = None
    start_time_eastern: str | None = None


class TranscriptTurn(BaseModel):
    sequence: int = 0
    timestamp: str | None = None
    end_timestamp: str | None = None
    speaker: str
    speaker_role: str
    text: str


class TranscriptChunk(BaseModel):
    transcript_id: str
    chunk_id: str
    start_timestamp: str | None = None
    end_timestamp: str | None = None
    turns: list[TranscriptTurn]


class PreparedTranscript(BaseModel):
    transcript_id: str
    metadata: TranscriptMetadata | None = None
    chunks: list[TranscriptChunk]


class CandidateSignal(BaseModel):
    transcript_id: str
    item_type: SignalType
    category: str
    advisor_quote: str
    timestamp: str | None = None
    evidence_strength: EvidenceStrength
    rationale: str
    source_chunk_id: str


class RankedSignal(CandidateSignal):
    rank: int = Field(ge=1, le=3)


class ValidatedSignal(RankedSignal):
    validation_notes: str


class FinalSignal(BaseModel):
    transcript_id: str
    item_type: SignalType
    rank: int = Field(ge=1, le=3)
    category: str
    advisor_quote: str
    timestamp: str | None = None
    evidence_strength: EvidenceStrength
    rationale: str


class PipelineOutputs(BaseModel):
    prepared_transcript: PreparedTranscript
    final_signals: list[FinalSignal]
