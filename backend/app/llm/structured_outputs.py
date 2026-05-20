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


class RankedSignalOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_candidate_id: str = Field(min_length=1)
    item_type: SignalType
    rank: int = Field(ge=1)
    category: str = Field(min_length=1)
    advisor_quote: str = Field(min_length=1)
    timestamp: str | None = None
    evidence_strength: EvidenceStrength
    rationale: str = Field(min_length=1)


class ConsolidationRankingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ranked_signals: list[RankedSignalOutput] = Field(default_factory=list)


class ValidatedSignalOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ranked_signal_id: str = Field(min_length=1)
    item_type: SignalType
    rank: int = Field(ge=1)
    category: str = Field(min_length=1)
    advisor_quote: str = Field(min_length=1)
    timestamp: str | None = None
    evidence_strength: EvidenceStrength
    rationale: str = Field(min_length=1)
    validation_notes: str = Field(min_length=1)


class RejectedSignalOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ranked_signal_id: str = Field(min_length=1)
    rejection_reason: str = Field(min_length=1)
    validation_notes: str = Field(min_length=1)


class EvidenceValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    validated_signals: list[ValidatedSignalOutput] = Field(default_factory=list)
    rejected_signals: list[RejectedSignalOutput] = Field(default_factory=list)
