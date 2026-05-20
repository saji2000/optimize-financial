from app.pipeline.agents.evidence_validation_agent import EvidenceValidationAgent
from app.pipeline.schemas import PreparedTranscript, RankedSignal, TranscriptChunk, TranscriptTurn


def _prepared_transcript() -> PreparedTranscript:
    return PreparedTranscript(
        transcript_id="call_001",
        chunks=[
            TranscriptChunk(
                transcript_id="call_001",
                chunk_id="call_001_chunk_001",
                turns=[
                    TranscriptTurn(
                        sequence=1,
                        timestamp="00:01:00",
                        speaker="Advisor",
                        speaker_role="advisor",
                        text="I need stronger operations support.",
                    ),
                    TranscriptTurn(
                        sequence=2,
                        timestamp="00:02:00",
                        speaker="Advisor",
                        speaker_role="advisor",
                        text="Clients can only handle so much transition.",
                    ),
                ],
            )
        ],
    )


def _ranked_signal(
    *,
    item_type: str,
    rank: int,
    advisor_quote: str,
    category: str = "Operational support",
) -> RankedSignal:
    return RankedSignal(
        transcript_id="call_001",
        source_chunk_id="call_001_chunk_001",
        item_type=item_type,
        rank=rank,
        category=category,
        advisor_quote=advisor_quote,
        timestamp="00:01:00",
        evidence_strength="explicit",
        rationale="The advisor states a decision-relevant signal.",
    )


def test_validation_re_numbers_remaining_signals_after_drops() -> None:
    ranked = [
        _ranked_signal(
            item_type="driver",
            rank=1,
            advisor_quote="This quote is not present.",
        ),
        _ranked_signal(
            item_type="driver",
            rank=2,
            advisor_quote="I need stronger operations support.",
        ),
        _ranked_signal(
            item_type="blocker",
            rank=1,
            advisor_quote="This blocker quote is absent.",
            category="Book portability",
        ),
        _ranked_signal(
            item_type="blocker",
            rank=2,
            advisor_quote="Clients can only handle so much transition.",
            category="Client disruption risk",
        ),
    ]

    validated = EvidenceValidationAgent().run(ranked, _prepared_transcript())

    assert [(item.item_type, item.rank, item.advisor_quote) for item in validated] == [
        ("driver", 1, "I need stronger operations support."),
        ("blocker", 1, "Clients can only handle so much transition."),
    ]
