from app.domain.enums import EvidenceStrength, SignalType
from app.domain.signal_schema import SignalCandidate


def test_signal_candidate_schema_accepts_expected_fields() -> None:
    candidate = SignalCandidate(
        id="candidate-1",
        transcript_id="transcript-1",
        signal_type=SignalType.DRIVER,
        category="pricing",
        summary="Advisor values predictable pricing.",
        evidence_quote="The pricing model is easy to explain.",
        evidence_strength=EvidenceStrength.EXPLICIT,
        rationale="Direct advisor quote supports the signal.",
    )

    assert candidate.signal_type == SignalType.DRIVER
