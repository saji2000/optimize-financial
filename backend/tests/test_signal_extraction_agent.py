import pytest
from pydantic import ValidationError

from app.domain.enums import EvidenceStrength, SignalType
from app.llm.openai_client import OpenAIClient
from app.llm.structured_outputs import SegmentSignalExtractionResult
from app.pipeline.agents.signal_extraction_agent import SignalExtractionAgent
from app.pipeline.schemas import PreparedTranscript, TranscriptChunk, TranscriptTurn
from scripts.run_signal_extraction_for_prepared import build_signal_extraction_agent


class FakeLLMClient:
    def __init__(self, results: list[object]) -> None:
        self.results = results
        self.calls: list[dict[str, object]] = []

    def parse_structured_output(self, **kwargs):
        self.calls.append(kwargs)
        return self.results.pop(0)


def _prepared_with_turns(turns: list[TranscriptTurn]) -> PreparedTranscript:
    return PreparedTranscript(
        transcript_id="call_sanitized",
        chunks=[
            TranscriptChunk(
                transcript_id="call_sanitized",
                chunk_id="call_sanitized_chunk_001",
                start_timestamp=turns[0].timestamp if turns else None,
                end_timestamp=turns[-1].end_timestamp if turns else None,
                turns=turns,
            )
        ],
    )


def _turn(
    *,
    text: str,
    speaker_role: str = "advisor",
    timestamp: str = "00:01:00",
) -> TranscriptTurn:
    return TranscriptTurn(
        sequence=1,
        timestamp=timestamp,
        end_timestamp=None,
        speaker="Advisor" if speaker_role == "advisor" else "Optimize Rep",
        speaker_role=speaker_role,
        text=text,
    )


def test_signal_extraction_extracts_driver_from_advisor_owned_motivation() -> None:
    llm_client = FakeLLMClient(
        [
            SegmentSignalExtractionResult.model_validate(
                {
                    "candidates": [
                        {
                            "item_type": "driver",
                            "category": "Operational support",
                            "advisor_quote": "I need stronger operations support.",
                            "timestamp": "00:01:00",
                            "evidence_strength": "explicit",
                            "rationale": "The advisor states a support need relevant to evaluating Optimize.",
                        }
                    ]
                }
            )
        ]
    )
    prepared = _prepared_with_turns([_turn(text="I need stronger operations support.")])

    candidates = SignalExtractionAgent(llm_client=llm_client).run(prepared)

    assert len(candidates) == 1
    assert candidates[0].item_type == SignalType.DRIVER
    assert candidates[0].category == "Operational support"


def test_signal_extraction_extracts_blocker_from_advisor_owned_concern() -> None:
    llm_client = FakeLLMClient(
        [
            SegmentSignalExtractionResult.model_validate(
                {
                    "candidates": [
                        {
                            "item_type": "blocker",
                            "category": "Transition complexity",
                            "advisor_quote": "The transition is what worries me most.",
                            "timestamp": "00:02:00",
                            "evidence_strength": "explicit",
                            "rationale": "The advisor directly identifies transition effort as a concern.",
                        }
                    ]
                }
            )
        ]
    )
    prepared = _prepared_with_turns(
        [_turn(text="The transition is what worries me most.", timestamp="00:02:00")]
    )

    candidates = SignalExtractionAgent(llm_client=llm_client).run(prepared)

    assert len(candidates) == 1
    assert candidates[0].item_type == SignalType.BLOCKER
    assert candidates[0].evidence_strength == EvidenceStrength.EXPLICIT


@pytest.mark.parametrize(
    ("turn", "reason"),
    [
        (
            _turn(
                text="Our platform has a strong service model.",
                speaker_role="optimize_rep",
            ),
            "rep-only claims are not advisor-owned signals",
        ),
        (
            _turn(text="Sounds good. Thursday afternoon works for me."),
            "polite interest and scheduling are not supported signals",
        ),
    ],
)
def test_signal_extraction_returns_empty_for_rejected_signal_types(
    turn: TranscriptTurn, reason: str
) -> None:
    llm_client = FakeLLMClient([SegmentSignalExtractionResult(candidates=[])])
    prepared = _prepared_with_turns([turn])

    candidates = SignalExtractionAgent(llm_client=llm_client).run(prepared)

    assert candidates == [], reason


def test_signal_extraction_adds_transcript_id_and_source_chunk_id_deterministically() -> None:
    llm_client = FakeLLMClient(
        [
            SegmentSignalExtractionResult.model_validate(
                {
                    "candidates": [
                        {
                            "item_type": "driver",
                            "category": "Business growth",
                            "advisor_quote": "I want to grow faster.",
                            "timestamp": "00:01:00",
                            "evidence_strength": "explicit",
                            "rationale": "The advisor names growth as a motivation.",
                        }
                    ]
                }
            )
        ]
    )
    prepared = _prepared_with_turns([_turn(text="I want to grow faster.")])

    candidate = SignalExtractionAgent(llm_client=llm_client).run(prepared)[0]

    assert candidate.transcript_id == "call_sanitized"
    assert candidate.source_chunk_id == "call_sanitized_chunk_001"


def test_signal_extraction_rejects_malformed_structured_output() -> None:
    malformed_payload = {
        "candidates": [
            {
                "item_type": "driver",
                "category": "Business growth",
                "advisor_quote": "I want to grow faster.",
                "timestamp": "00:01:00",
                "evidence_strength": "explicit",
                "rationale": "The advisor names growth as a motivation.",
                "unexpected": "not allowed",
            }
        ]
    }
    llm_client = FakeLLMClient([malformed_payload])
    prepared = _prepared_with_turns([_turn(text="I want to grow faster.")])

    with pytest.raises(ValidationError):
        SignalExtractionAgent(llm_client=llm_client).run(prepared)


def test_local_signal_extraction_script_disables_usage_recording_by_default() -> None:
    agent = build_signal_extraction_agent(record_usage=False)

    assert isinstance(agent.llm_client, OpenAIClient)
    assert agent.llm_client.usage_recorder is None
