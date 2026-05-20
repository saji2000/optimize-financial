import json

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.domain.enums import EvidenceStrength, SignalType
from app.llm.openai_client import OpenAIClient
from app.llm.structured_outputs import FinalFormattingResult
from app.pipeline.agents.final_formatting_agent import FinalFormattingAgent
from app.pipeline.schemas import ValidatedSignal
from scripts.run_final_formatting_for_validated import (
    build_final_formatting_agent,
    validated_items,
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


def _validated_signal(
    *,
    transcript_id: str = "call_sanitized",
    item_type: SignalType | str = SignalType.DRIVER,
    rank: int = 1,
    category: str = "Operational support",
    advisor_quote: str = "I need stronger operations support.",
    timestamp: str | None = "00:01:00",
    evidence_strength: EvidenceStrength | str = EvidenceStrength.EXPLICIT,
    rationale: str = "The advisor states a support need.",
    source_chunk_id: str = "call_sanitized_chunk_001",
    validation_notes: str = "The quote appears in an advisor turn.",
) -> ValidatedSignal:
    return ValidatedSignal(
        transcript_id=transcript_id,
        item_type=item_type,
        rank=rank,
        category=category,
        advisor_quote=advisor_quote,
        timestamp=timestamp,
        evidence_strength=evidence_strength,
        rationale=rationale,
        source_chunk_id=source_chunk_id,
        validation_notes=validation_notes,
    )


def _result(items: list[dict] | None = None) -> FinalFormattingResult:
    return FinalFormattingResult.model_validate({"final_signals": items or []})


def _final_item(
    *,
    source_validated_signal_id: str = "validated_signal_001",
    item_type: str = "driver",
    rank: int = 1,
    category: str = "Operational support",
    advisor_quote: str = "I need stronger operations support.",
    timestamp: str | None = "00:01:00",
    evidence_strength: str = "explicit",
    rationale: str = "The advisor states a support need.",
) -> dict:
    return {
        "source_validated_signal_id": source_validated_signal_id,
        "item_type": item_type,
        "rank": rank,
        "category": category,
        "advisor_quote": advisor_quote,
        "timestamp": timestamp,
        "evidence_strength": evidence_strength,
        "rationale": rationale,
    }


def test_empty_input_returns_empty_and_makes_no_llm_call() -> None:
    llm_client = FakeLLMClient([])

    final = FinalFormattingAgent(llm_client=llm_client).run([])

    assert final == []
    assert llm_client.calls == []


def test_model_defaults_to_settings_openai_model_mid() -> None:
    llm_client = FakeLLMClient([_result()])

    FinalFormattingAgent(llm_client=llm_client).run([_validated_signal()])

    assert settings.openai_model_mid == "gpt-5.4"
    assert llm_client.calls[0]["model"] == settings.openai_model_mid
    assert llm_client.calls[0]["endpoint"] == "responses"
    assert llm_client.calls[0]["service_tier"] == "flex"
    assert llm_client.calls[0]["max_output_tokens"] == 3000


def test_input_payload_uses_validated_ids_and_excludes_internal_fields() -> None:
    payload = FinalFormattingAgent(llm_client=FakeLLMClient([])).input_payload(
        [_validated_signal()]
    )

    assert payload["transcript_id"] == "call_sanitized"
    assert payload["validated_signal_count"] == 1
    assert payload["validated_signals"][0]["validated_signal_id"] == "validated_signal_001"
    assert "validation_notes" not in payload["validated_signals"][0]
    assert "source_chunk_id" not in payload["validated_signals"][0]


def test_llm_output_becomes_public_final_signal_without_internal_fields() -> None:
    llm_client = FakeLLMClient([_result([_final_item()])])

    final = FinalFormattingAgent(llm_client=llm_client).run([_validated_signal()])

    assert len(final) == 1
    assert final[0].transcript_id == "call_sanitized"
    assert final[0].category == "Operational support"
    dumped = final[0].model_dump(mode="json")
    assert "validation_notes" not in dumped
    assert "source_chunk_id" not in dumped


def test_unknown_source_validated_signal_id_fails() -> None:
    llm_client = FakeLLMClient(
        [_result([_final_item(source_validated_signal_id="validated_signal_999")])]
    )

    with pytest.raises(ValueError, match="Unknown source_validated_signal_id"):
        FinalFormattingAgent(llm_client=llm_client).run([_validated_signal()])


def test_duplicate_source_validated_signal_id_fails() -> None:
    llm_client = FakeLLMClient([_result([_final_item(), _final_item(rank=2)])])

    with pytest.raises(ValueError, match="Duplicate source_validated_signal_id"):
        FinalFormattingAgent(llm_client=llm_client).run([_validated_signal()])


def test_item_type_mismatch_fails() -> None:
    llm_client = FakeLLMClient([_result([_final_item(item_type="blocker")])])

    with pytest.raises(ValueError, match="item_type does not match"):
        FinalFormattingAgent(llm_client=llm_client).run(
            [_validated_signal(item_type=SignalType.DRIVER)]
        )


def test_outputs_are_capped_and_ranks_repaired_per_item_type() -> None:
    llm_client = FakeLLMClient(
        [
            _result(
                [
                    _final_item(source_validated_signal_id="validated_signal_001", rank=2),
                    _final_item(source_validated_signal_id="validated_signal_002", rank=4),
                    _final_item(source_validated_signal_id="validated_signal_003", rank=5),
                    _final_item(source_validated_signal_id="validated_signal_004", rank=6),
                    _final_item(
                        source_validated_signal_id="validated_signal_005",
                        item_type="blocker",
                        rank=3,
                        category="Transition complexity",
                        advisor_quote="The transition worries me.",
                        rationale="The advisor states a transition concern.",
                    ),
                ]
            )
        ]
    )
    validated = [
        _validated_signal(rank=1, advisor_quote="I need support area one."),
        _validated_signal(rank=2, advisor_quote="I need support area two."),
        _validated_signal(rank=3, advisor_quote="I need support area three."),
        _validated_signal(rank=3, advisor_quote="I need support area four."),
        _validated_signal(
            item_type=SignalType.BLOCKER,
            category="Transition complexity",
            advisor_quote="The transition worries me.",
            rationale="The advisor states a transition concern.",
        ),
    ]

    final = FinalFormattingAgent(llm_client=llm_client).run(validated)

    assert [(item.item_type, item.rank) for item in final] == [
        (SignalType.DRIVER, 1),
        (SignalType.DRIVER, 2),
        (SignalType.DRIVER, 3),
        (SignalType.BLOCKER, 1),
    ]


def test_malformed_structured_output_is_rejected() -> None:
    malformed_payload = {"final_signals": [{**_final_item(), "validation_notes": "hidden"}]}
    llm_client = FakeLLMClient([malformed_payload])

    with pytest.raises(ValidationError):
        FinalFormattingAgent(llm_client=llm_client).run([_validated_signal()])


def test_local_final_formatting_script_disables_usage_recording_by_default() -> None:
    agent = build_final_formatting_agent(record_usage=False)

    assert isinstance(agent.llm_client, OpenAIClient)
    assert agent.llm_client.usage_recorder is None


def test_validated_script_parser_accepts_artifact_envelope() -> None:
    validated_json = [_validated_signal().model_dump(mode="json")]
    envelope = {"transcript_id": "call_sanitized", "output": validated_json}

    parsed = validated_items(json.loads(json.dumps(envelope)))

    assert parsed == validated_json
