import json

import pytest

from app.domain.enums import EvidenceStrength, SignalType
from app.pipeline.agents.final_formatting_agent import FinalFormatter, FinalFormattingAgent
from app.pipeline.schemas import ValidatedSignal
from scripts.run_final_formatting_for_validated import (
    build_final_formatter,
    validated_items,
)


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


def test_empty_input_returns_empty_output() -> None:
    assert FinalFormatter().run([]) == []


def test_temporary_agent_alias_points_to_formatter() -> None:
    assert FinalFormattingAgent is FinalFormatter


def test_internal_fields_are_excluded_from_public_output() -> None:
    final = FinalFormatter().run([_validated_signal()])

    dumped = final[0].model_dump(mode="json")
    assert "validation_notes" not in dumped
    assert "source_chunk_id" not in dumped


def test_mixed_driver_and_blocker_inputs_preserve_public_fields() -> None:
    driver = _validated_signal(rank=2)
    blocker = _validated_signal(
        item_type=SignalType.BLOCKER,
        rank=1,
        category="Transition complexity",
        advisor_quote="The transition worries me.",
        timestamp="00:02:00",
        evidence_strength=EvidenceStrength.IMPLIED,
        rationale="The advisor names a transition concern.",
    )

    final = FinalFormatter().run([blocker, driver])

    assert [signal.item_type for signal in final] == [
        SignalType.DRIVER,
        SignalType.BLOCKER,
    ]
    assert final[0].rank == 1
    assert final[0].category == driver.category
    assert final[0].advisor_quote == driver.advisor_quote
    assert final[0].timestamp == driver.timestamp
    assert final[0].evidence_strength == driver.evidence_strength
    assert final[0].rationale == driver.rationale
    assert final[1].rank == 1
    assert final[1].category == blocker.category


def test_rank_gaps_are_repaired_per_item_type() -> None:
    validated = [
        _validated_signal(rank=1, advisor_quote="First driver."),
        _validated_signal(rank=3, advisor_quote="Third driver."),
        _validated_signal(
            item_type=SignalType.BLOCKER,
            rank=2,
            category="Timing",
            advisor_quote="Timing is hard.",
        ),
    ]

    final = FinalFormatter().run(validated)

    assert [(item.item_type, item.rank) for item in final] == [
        (SignalType.DRIVER, 1),
        (SignalType.DRIVER, 2),
        (SignalType.BLOCKER, 1),
    ]


def test_more_than_three_per_type_are_capped() -> None:
    validated = [
        _validated_signal(rank=1, advisor_quote="Driver one."),
        _validated_signal(rank=1, advisor_quote="Driver two."),
        _validated_signal(rank=2, advisor_quote="Driver three."),
        _validated_signal(rank=3, advisor_quote="Driver four."),
        _validated_signal(
            item_type=SignalType.BLOCKER,
            rank=1,
            category="Timing",
            advisor_quote="Timing is hard.",
        ),
    ]

    final = FinalFormatter().run(validated)

    assert [item.advisor_quote for item in final if item.item_type == SignalType.DRIVER] == [
        "Driver one.",
        "Driver two.",
        "Driver three.",
    ]
    assert [(item.item_type, item.rank) for item in final] == [
        (SignalType.DRIVER, 1),
        (SignalType.DRIVER, 2),
        (SignalType.DRIVER, 3),
        (SignalType.BLOCKER, 1),
    ]


def test_mixed_transcript_ids_raise_value_error() -> None:
    with pytest.raises(ValueError, match="FinalFormatter requires signals from one transcript"):
        FinalFormatter().run(
            [
                _validated_signal(transcript_id="call_sanitized"),
                _validated_signal(transcript_id="other_call"),
            ]
        )


def test_no_llm_client_is_required_or_called() -> None:
    formatter = build_final_formatter()

    assert not hasattr(formatter, "llm_client")
    assert len(formatter.run([_validated_signal()])) == 1


def test_validated_script_parser_accepts_artifact_envelope() -> None:
    validated_json = [_validated_signal().model_dump(mode="json")]
    envelope = {"transcript_id": "call_sanitized", "output": validated_json}

    parsed = validated_items(json.loads(json.dumps(envelope)))

    assert parsed == validated_json
