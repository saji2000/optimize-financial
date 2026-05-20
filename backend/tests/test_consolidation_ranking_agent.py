import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.domain.enums import EvidenceStrength, SignalType
from app.llm.openai_client import OpenAIClient
from app.llm.structured_outputs import ConsolidationRankingResult
from app.pipeline.agents.consolidation_ranking_agent import ConsolidationRankingAgent
from app.pipeline.schemas import CandidateSignal
from scripts.run_consolidation_ranking_for_candidates import (
    build_consolidation_ranking_agent,
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


def _candidate(
    *,
    item_type: SignalType | str = SignalType.DRIVER,
    category: str = "Operational support",
    advisor_quote: str = "I need stronger operations support.",
    timestamp: str | None = "00:01:00",
    evidence_strength: EvidenceStrength | str = EvidenceStrength.EXPLICIT,
    rationale: str = "The advisor states a support need.",
    source_chunk_id: str = "call_sanitized_chunk_001",
) -> CandidateSignal:
    return CandidateSignal(
        transcript_id="call_sanitized",
        item_type=item_type,
        category=category,
        advisor_quote=advisor_quote,
        timestamp=timestamp,
        evidence_strength=evidence_strength,
        rationale=rationale,
        source_chunk_id=source_chunk_id,
    )


def _result(items: list[dict]) -> ConsolidationRankingResult:
    return ConsolidationRankingResult.model_validate({"ranked_signals": items})


def _ranked_item(
    *,
    source_candidate_id: str = "candidate_001",
    item_type: str = "driver",
    rank: int = 1,
    category: str = "Operational support",
    advisor_quote: str = "I need stronger operations support.",
    timestamp: str | None = "00:01:00",
    evidence_strength: str = "explicit",
    rationale: str = "The advisor states a support need.",
) -> dict:
    return {
        "source_candidate_id": source_candidate_id,
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

    ranked = ConsolidationRankingAgent(llm_client=llm_client).run([])

    assert ranked == []
    assert llm_client.calls == []


def test_model_defaults_to_settings_openai_model() -> None:
    llm_client = FakeLLMClient([ConsolidationRankingResult()])

    ConsolidationRankingAgent(llm_client=llm_client).run([_candidate()])

    assert settings.openai_model == "gpt-5.5"
    assert llm_client.calls[0]["model"] == settings.openai_model
    assert llm_client.calls[0]["endpoint"] == "responses"
    assert llm_client.calls[0]["service_tier"] == "standard"
    assert llm_client.calls[0]["max_output_tokens"] == 6000


def test_constructor_can_override_model() -> None:
    llm_client = FakeLLMClient([ConsolidationRankingResult()])

    ConsolidationRankingAgent(llm_client=llm_client, model="gpt-custom").run(
        [_candidate()]
    )

    assert llm_client.calls[0]["model"] == "gpt-custom"


def test_retryable_primary_model_failure_falls_back_to_mid_model() -> None:
    llm_client = FakeLLMClient([RetryableOpenAIError("server error"), _result([])])

    ranked = ConsolidationRankingAgent(llm_client=llm_client).run([_candidate()])

    assert ranked == []
    assert [call["model"] for call in llm_client.calls] == [
        settings.openai_model,
        settings.openai_model_mid,
    ]


def test_non_retryable_primary_model_failure_does_not_fall_back() -> None:
    llm_client = FakeLLMClient([ValueError("bad local output")])

    with pytest.raises(ValueError, match="bad local output"):
        ConsolidationRankingAgent(llm_client=llm_client).run([_candidate()])

    assert len(llm_client.calls) == 1


def test_duplicate_candidates_collapse_into_one_ranked_signal() -> None:
    llm_client = FakeLLMClient([_result([_ranked_item()])])
    candidates = [
        _candidate(),
        _candidate(
            advisor_quote="What I really need is better operational support.",
            source_chunk_id="call_sanitized_chunk_002",
        ),
    ]

    ranked = ConsolidationRankingAgent(llm_client=llm_client).run(candidates)

    assert len(ranked) == 1
    assert ranked[0].rank == 1
    assert ranked[0].source_chunk_id == "call_sanitized_chunk_001"
    payload = llm_client.calls[0]["input_payload"]
    assert payload["candidate_count"] == 2
    assert [item["candidate_id"] for item in payload["candidates"]] == [
        "candidate_001",
        "candidate_002",
    ]


def test_ranks_are_separate_for_drivers_and_blockers() -> None:
    llm_client = FakeLLMClient(
        [
            _result(
                [
                    _ranked_item(source_candidate_id="candidate_001", item_type="driver"),
                    _ranked_item(
                        source_candidate_id="candidate_002",
                        item_type="blocker",
                        category="Transition complexity",
                        advisor_quote="The transition worries me.",
                        rationale="The advisor states a transition concern.",
                    ),
                ]
            )
        ]
    )
    candidates = [
        _candidate(),
        _candidate(
            item_type=SignalType.BLOCKER,
            category="Transition complexity",
            advisor_quote="The transition worries me.",
            rationale="The advisor states a transition concern.",
            source_chunk_id="call_sanitized_chunk_002",
        ),
    ]

    ranked = ConsolidationRankingAgent(llm_client=llm_client).run(candidates)

    assert [(item.item_type, item.rank) for item in ranked] == [
        (SignalType.DRIVER, 1),
        (SignalType.BLOCKER, 1),
    ]


def test_output_is_capped_at_three_per_type() -> None:
    llm_client = FakeLLMClient(
        [
            _result(
                [
                    _ranked_item(source_candidate_id=f"candidate_{index:03d}", rank=index)
                    for index in range(1, 5)
                ]
            )
        ]
    )
    candidates = [
        _candidate(
            category=f"Driver {index}",
            advisor_quote=f"I need support area {index}.",
            source_chunk_id=f"call_sanitized_chunk_{index:03d}",
        )
        for index in range(1, 5)
    ]

    ranked = ConsolidationRankingAgent(llm_client=llm_client).run(candidates)

    assert len(ranked) == 3
    assert [item.rank for item in ranked] == [1, 2, 3]


def test_unknown_source_candidate_id_raises_validation_error() -> None:
    llm_client = FakeLLMClient(
        [_result([_ranked_item(source_candidate_id="candidate_999")])]
    )

    with pytest.raises(ValueError, match="Unknown source_candidate_id"):
        ConsolidationRankingAgent(llm_client=llm_client).run([_candidate()])


def test_non_contiguous_ranks_are_rejected() -> None:
    llm_client = FakeLLMClient(
        [
            _result(
                [
                    _ranked_item(source_candidate_id="candidate_001", rank=1),
                    _ranked_item(source_candidate_id="candidate_002", rank=3),
                ]
            )
        ]
    )

    with pytest.raises(ValueError, match="ranks must be contiguous"):
        ConsolidationRankingAgent(llm_client=llm_client).run(
            [_candidate(), _candidate(source_chunk_id="call_sanitized_chunk_002")]
        )


def test_malformed_structured_output_is_rejected() -> None:
    malformed_payload = {
        "ranked_signals": [
            {
                **_ranked_item(),
                "unexpected": "not allowed",
            }
        ]
    }
    llm_client = FakeLLMClient([malformed_payload])

    with pytest.raises(ValidationError):
        ConsolidationRankingAgent(llm_client=llm_client).run([_candidate()])


def test_local_consolidation_script_disables_usage_recording_by_default() -> None:
    agent = build_consolidation_ranking_agent(record_usage=False)

    assert isinstance(agent.llm_client, OpenAIClient)
    assert agent.llm_client.usage_recorder is None
