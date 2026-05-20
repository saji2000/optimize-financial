from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import EvidenceStrength, SignalType


def require_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Expected structured object output")
    return payload


class SegmentCandidateSignalOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: SignalType
    category: str = Field(min_length=1)
    advisor_quote: str = Field(min_length=1)
    timestamp: str | None = None
    evidence_strength: EvidenceStrength
    rationale: str = Field(min_length=1)


class SegmentSignalExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[SegmentCandidateSignalOutput] = Field(default_factory=list)
