from app.domain.signal_schema import SignalCandidate, SignalRead


def finalize_candidates(candidates: list[SignalCandidate]) -> list[SignalRead]:
    ranks = {"driver": 0, "blocker": 0}
    finalized: list[SignalRead] = []
    for candidate in candidates:
        item_type = candidate.signal_type.value
        ranks[item_type] += 1
        finalized.append(
            SignalRead(
                id=candidate.id,
                transcript_id=candidate.transcript_id,
                item_type=candidate.signal_type,
                rank=ranks[item_type],
                category=candidate.category,
                advisor_quote=candidate.evidence_quote,
                timestamp=None,
                evidence_strength=candidate.evidence_strength,
                rationale=candidate.rationale,
            )
        )
    return finalized
