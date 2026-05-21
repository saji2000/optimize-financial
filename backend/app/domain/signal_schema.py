from pydantic import BaseModel

from app.domain.enums import EvidenceStrength, SignalType


class SignalCandidate(BaseModel):
    id: str
    transcript_id: str
    signal_type: SignalType
    category: str
    summary: str
    evidence_quote: str
    evidence_strength: EvidenceStrength
    rationale: str


class SignalRead(BaseModel):
    id: str
    transcript_id: str
    item_type: SignalType
    rank: int
    category: str
    advisor_quote: str
    timestamp: str | None = None
    evidence_strength: EvidenceStrength
    rationale: str
