import json

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.domain.enums import EvidenceStrength, SignalType
from app.llm.openai_client import OpenAIClient
from app.llm.structured_outputs import EvidenceValidationResult
from app.pipeline.agents.evidence_validation_agent import EvidenceValidationAgent
from app.pipeline.schemas import PreparedTranscript, RankedSignal, TranscriptChunk, TranscriptTurn
from scripts.run_evidence_validation_for_ranked import (
    build_evidence_validation_agent,
    prepared_transcript_payload,
    ranked_items,
)


class FakeLLMClient:
    def __init__(self, results: list[object]) -> None:
        self.results = results
        self.calls: list[dict[str, object]] = []

    def parse_structured_output(self, **kwargs):
        self.calls.append(kwargs)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class RetryableOpenAIError(Exception):
    status_code = 500


def _prepared_transcript() -> PreparedTranscript:
    return PreparedTranscript(
        transcript_id="call_sanitized",
        chunks=[
            TranscriptChunk(
                transcript_id="call_sanitized",
                chunk_id="call_sanitized_chunk_001",
                start_timestamp="00:00:55",
                end_timestamp="00:02:15",
                turns=[
                    TranscriptTurn(
                        sequence=1,
                        timestamp="00:00:55",
                        speaker="Optimize Rep",
                        speaker_role="optimize_rep",
                        text="Tell me what would make a transition worthwhile.",
                    ),
                    TranscriptTurn(
                        sequence=2,
                        timestamp="00:01:00",
                        speaker="Advisor",
                        speaker_role="advisor",
                        text="I need stronger operations support.",
                    ),
                    TranscriptTurn(
                        sequence=3,
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
    item_type: SignalType | str = SignalType.DRIVER,
    rank: int = 1,
    advisor_quote: str = "I need stronger operations support.",
    category: str = "Operational support",
    source_chunk_id: str = "call_sanitized_chunk_001",
) -> RankedSignal:
    return RankedSignal(
        transcript_id="call_sanitized",
        source_chunk_id=source_chunk_id,
        item_type=item_type,
        rank=rank,
        category=category,
        advisor_quote=advisor_quote,
        timestamp="00:01:00",
        evidence_strength=EvidenceStrength.EXPLICIT,
        rationale="The advisor states a decision-relevant signal.",
    )


def _result(
    *,
    validated: list[dict] | None = None,
    rejected: list[dict] | None = None,
) -> EvidenceValidationResult:
    return EvidenceValidationResult.model_validate(
        {
            "validated_signals": validated or [],
            "rejected_signals": rejected or [],
        }
    )


def _validated_item(
    *,
    source_ranked_signal_id: str = "ranked_signal_001",
    item_type: str = "driver",
    rank: int = 1,
    category: str = "Operational support",
    advisor_quote: str = "I need stronger operations support.",
    timestamp: str | None = "00:01:00",
    evidence_strength: str = "explicit",
    rationale: str = "The advisor states a support need.",
    validation_notes: str = "The quote appears in an advisor turn.",
) -> dict:
    return {
        "source_ranked_signal_id": source_ranked_signal_id,
        "item_type": item_type,
        "rank": rank,
        "category": category,
        "advisor_quote": advisor_quote,
        "timestamp": timestamp,
        "evidence_strength": evidence_strength,
        "rationale": rationale,
        "validation_notes": validation_notes,
    }


def _rejected_item(
    *,
    source_ranked_signal_id: str = "ranked_signal_001",
    rejection_reason: str = "Quote is not advisor-owned.",
    validation_notes: str = "The support came from representative messaging.",
) -> dict:
    return {
        "source_ranked_signal_id": source_ranked_signal_id,
        "rejection_reason": rejection_reason,
        "validation_notes": validation_notes,
    }


def test_empty_ranked_input_returns_empty_and_makes_no_llm_call() -> None:
    llm_client = FakeLLMClient([])

    validated = EvidenceValidationAgent(llm_client=llm_client).run([])

    assert validated == []
    assert llm_client.calls == []


def test_model_defaults_to_settings_openai_model() -> None:
    llm_client = FakeLLMClient([_result(rejected=[_rejected_item()])])

    EvidenceValidationAgent(llm_client=llm_client).run(
        [_ranked_signal()],
        _prepared_transcript(),
    )

    assert settings.openai_model == "gpt-5.5"
    assert llm_client.calls[0]["model"] == settings.openai_model
    assert llm_client.calls[0]["endpoint"] == "responses"
    assert llm_client.calls[0]["service_tier"] == "flex"
    assert llm_client.calls[0]["max_output_tokens"] == 6000


def test_constructor_can_override_model() -> None:
    llm_client = FakeLLMClient([_result(rejected=[_rejected_item()])])

    EvidenceValidationAgent(llm_client=llm_client, model="gpt-custom").run(
        [_ranked_signal()],
        _prepared_transcript(),
    )

    assert llm_client.calls[0]["model"] == "gpt-custom"


def test_accepted_signals_become_validated_signals() -> None:
    llm_client = FakeLLMClient([_result(validated=[_validated_item()])])

    validated = EvidenceValidationAgent(llm_client=llm_client).run(
        [_ranked_signal()],
        _prepared_transcript(),
    )

    assert len(validated) == 1
    assert validated[0].transcript_id == "call_sanitized"
    assert validated[0].source_chunk_id == "call_sanitized_chunk_001"
    assert validated[0].category == "Operational support"
    assert validated[0].validation_notes == "The quote appears in an advisor turn."


def test_rejected_signals_are_dropped() -> None:
    llm_client = FakeLLMClient([_result(rejected=[_rejected_item()])])

    validated = EvidenceValidationAgent(llm_client=llm_client).run(
        [_ranked_signal()],
        _prepared_transcript(),
    )

    assert validated == []


def test_remaining_ranks_are_contiguous_per_item_type() -> None:
    llm_client = FakeLLMClient(
        [
            _result(
                validated=[
                    _validated_item(
                        source_ranked_signal_id="ranked_signal_002",
                        item_type="driver",
                        rank=2,
                        advisor_quote="I need stronger operations support.",
                    ),
                    _validated_item(
                        source_ranked_signal_id="ranked_signal_004",
                        item_type="blocker",
                        rank=2,
                        category="Client disruption risk",
                        advisor_quote="Clients can only handle so much transition.",
                    ),
                ],
                rejected=[
                    _rejected_item(source_ranked_signal_id="ranked_signal_001"),
                    _rejected_item(source_ranked_signal_id="ranked_signal_003"),
                ],
            )
        ]
    )
    ranked = [
        _ranked_signal(rank=1, advisor_quote="Unsupported driver."),
        _ranked_signal(rank=2),
        _ranked_signal(
            item_type=SignalType.BLOCKER,
            rank=1,
            advisor_quote="Unsupported blocker.",
            category="Transition complexity",
        ),
        _ranked_signal(
            item_type=SignalType.BLOCKER,
            rank=2,
            advisor_quote="Clients can only handle so much transition.",
            category="Client disruption risk",
        ),
    ]

    validated = EvidenceValidationAgent(llm_client=llm_client).run(
        ranked,
        _prepared_transcript(),
    )

    assert [(item.item_type, item.rank, item.advisor_quote) for item in validated] == [
        (SignalType.DRIVER, 1, "I need stronger operations support."),
        (SignalType.BLOCKER, 1, "Clients can only handle so much transition."),
    ]


def test_unknown_source_ranked_signal_id_fails() -> None:
    llm_client = FakeLLMClient(
        [_result(validated=[_validated_item(source_ranked_signal_id="ranked_signal_999")])]
    )

    with pytest.raises(ValueError, match="Unknown source_ranked_signal_id"):
        EvidenceValidationAgent(llm_client=llm_client).run(
            [_ranked_signal()],
            _prepared_transcript(),
        )


def test_duplicate_source_ranked_signal_id_fails() -> None:
    llm_client = FakeLLMClient(
        [
            _result(
                validated=[_validated_item()],
                rejected=[_rejected_item()],
            )
        ]
    )

    with pytest.raises(ValueError, match="Duplicate source_ranked_signal_id"):
        EvidenceValidationAgent(llm_client=llm_client).run(
            [_ranked_signal()],
            _prepared_transcript(),
        )


def test_missing_source_ranked_signal_id_fails() -> None:
    llm_client = FakeLLMClient([EvidenceValidationResult()])

    with pytest.raises(ValueError, match="Missing validation result"):
        EvidenceValidationAgent(llm_client=llm_client).run(
            [_ranked_signal()],
            _prepared_transcript(),
        )


def test_item_type_mismatch_fails() -> None:
    llm_client = FakeLLMClient([_result(validated=[_validated_item(item_type="blocker")])])

    with pytest.raises(ValueError, match="item_type does not match"):
        EvidenceValidationAgent(llm_client=llm_client).run(
            [_ranked_signal(item_type=SignalType.DRIVER)],
            _prepared_transcript(),
        )


def test_retryable_primary_model_failure_falls_back_to_mid_model() -> None:
    llm_client = FakeLLMClient(
        [RetryableOpenAIError("server error"), _result(rejected=[_rejected_item()])]
    )

    validated = EvidenceValidationAgent(llm_client=llm_client).run(
        [_ranked_signal()],
        _prepared_transcript(),
    )

    assert validated == []
    assert [call["model"] for call in llm_client.calls] == [
        settings.openai_model,
        settings.openai_model_mid,
    ]


def test_non_retryable_primary_model_failure_does_not_fall_back() -> None:
    llm_client = FakeLLMClient([ValueError("bad local output")])

    with pytest.raises(ValueError, match="bad local output"):
        EvidenceValidationAgent(llm_client=llm_client).run(
            [_ranked_signal()],
            _prepared_transcript(),
        )

    assert len(llm_client.calls) == 1


def test_malformed_structured_output_is_rejected() -> None:
    malformed_payload = {
        "validated_signals": [
            {
                **_validated_item(),
                "unexpected": "not allowed",
            }
        ],
        "rejected_signals": [],
    }
    llm_client = FakeLLMClient([malformed_payload])

    with pytest.raises(ValidationError):
        EvidenceValidationAgent(llm_client=llm_client).run(
            [_ranked_signal()],
            _prepared_transcript(),
        )
    assert len(llm_client.calls) == 1


def test_exact_quote_context_includes_matching_advisor_turn_and_neighbors() -> None:
    payload = EvidenceValidationAgent(llm_client=FakeLLMClient([])).input_payload(
        [_ranked_signal()],
        _prepared_transcript(),
    )

    context = payload["evidence_contexts"][0]
    assert context["match_type"] == "advisor_quote_exact_normalized_match"
    assert [turn["sequence"] for turn in context["turns"]] == [1, 2, 3]


def test_no_exact_quote_match_includes_full_source_chunk() -> None:
    payload = EvidenceValidationAgent(llm_client=FakeLLMClient([])).input_payload(
        [_ranked_signal(advisor_quote="A near verbatim support need.")],
        _prepared_transcript(),
    )

    context = payload["evidence_contexts"][0]
    assert context["match_type"] == "full_source_chunk_no_exact_advisor_quote_match"
    assert [turn["sequence"] for turn in context["turns"]] == [1, 2, 3]


def test_local_validation_script_disables_usage_recording_by_default() -> None:
    agent = build_evidence_validation_agent(record_usage=False)

    assert isinstance(agent.llm_client, OpenAIClient)
    assert agent.llm_client.usage_recorder is None


def test_ranked_script_parser_accepts_artifact_envelope() -> None:
    ranked_json = [_ranked_signal().model_dump(mode="json")]
    envelope = {"transcript_id": "call_sanitized", "output": ranked_json}

    parsed = ranked_items(json.loads(json.dumps(envelope)))

    assert parsed == ranked_json


def test_prepared_script_parser_accepts_artifact_envelope() -> None:
    prepared_json = _prepared_transcript().model_dump(mode="json")
    envelope = {"transcript_id": "call_sanitized", "output": prepared_json}

    parsed = prepared_transcript_payload(json.loads(json.dumps(envelope)))

    assert parsed == prepared_json
