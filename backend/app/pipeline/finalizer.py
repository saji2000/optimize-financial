from app.domain.signal_schema import SignalCandidate, SignalRead


def finalize_candidates(candidates: list[SignalCandidate]) -> list[SignalRead]:
    return [
        SignalRead(
            id=candidate.id,
            transcript_id=candidate.transcript_id,
            signal_type=candidate.signal_type,
            category=candidate.category,
            summary=candidate.summary,
            evidence_quote=candidate.evidence_quote,
            evidence_strength=candidate.evidence_strength,
            rationale=candidate.rationale,
        )
        for candidate in candidates
    ]

