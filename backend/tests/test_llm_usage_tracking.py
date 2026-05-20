from types import SimpleNamespace

import pytest

from app.llm.openai_client import LLMCallContext, OpenAIClient
from app.llm.structured_outputs import (
    ConsolidationRankingResult,
    SegmentSignalExtractionResult,
)
from app.pipeline.agents.consolidation_ranking_agent import ConsolidationRankingAgent
from app.pipeline.agents.signal_extraction_agent import SignalExtractionAgent
from app.pipeline.schemas import (
    CandidateSignal,
    PreparedTranscript,
    TranscriptChunk,
    TranscriptTurn,
)


class RecordingUsageRecorder:
    def __init__(self) -> None:
        self.events = []

    def record(self, event) -> None:
        self.events.append(event)


class FailingUsageRecorder:
    def record(self, event) -> None:
        raise RuntimeError("usage store unavailable")


class AuthenticationError(Exception):
    pass


class FakeCompletions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests = []

    def parse(self, **request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeResponses:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests = []

    def parse(self, **request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeSDK:
    def __init__(self, responses: list[object]) -> None:
        self.completions = FakeCompletions(responses)
        self.responses = FakeResponses(responses)
        self.beta = SimpleNamespace(
            chat=SimpleNamespace(completions=self.completions),
        )


def _response(payload: dict, prompt_tokens: int = 100, completion_tokens: int = 20):
    parsed = SegmentSignalExtractionResult.model_validate(payload)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed, content=None))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
    )


def _consolidation_response(
    payload: dict,
    prompt_tokens: int = 100,
    completion_tokens: int = 20,
):
    parsed = ConsolidationRankingResult.model_validate(payload)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed, content=None))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
    )


def _responses_response(payload: dict, input_tokens: int = 100, output_tokens: int = 20):
    parsed = SegmentSignalExtractionResult.model_validate(payload)
    return SimpleNamespace(
        output_parsed=parsed,
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
    )


def _context(chunk_id: str = "call_sanitized_chunk_001") -> LLMCallContext:
    return LLMCallContext(
        pipeline_run_id="run_sanitized",
        transcript_id="call_sanitized",
        chunk_id=chunk_id,
        agent_name="SignalExtractionAgent",
        pipeline_step="segment_signal_extraction",
        prompt_version="signal_extraction_v1",
    )


def test_successful_chunk_call_records_usage_tokens_cost_latency_and_status() -> None:
    recorder = RecordingUsageRecorder()
    client = OpenAIClient(
        sdk_client=FakeSDK([_response({"candidates": []})]),
        usage_recorder=recorder,
        attempts=1,
    )

    result = client.parse_structured_output(
        model="gpt-5.4",
        system_prompt="Extract signals.",
        input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
        response_model=SegmentSignalExtractionResult,
        context=_context(),
    )

    assert result.candidates == []
    request = client.sdk_client.completions.requests[0]
    assert request["service_tier"] == "flex"
    event = recorder.events[0]
    assert event.model == "gpt-5.4"
    assert event.prompt_version == "signal_extraction_v1"
    assert event.input_tokens == 100
    assert event.output_tokens == 20
    assert event.total_tokens == 120
    assert event.estimated_input_cost_usd == pytest.approx(0.00025)
    assert event.estimated_output_cost_usd == pytest.approx(0.0003)
    assert event.estimated_total_cost_usd == pytest.approx(0.00055)
    assert event.latency_ms >= 0
    assert event.retry_count == 0
    assert event.status == "success"
    assert event.error_type is None


def test_chunk_call_can_override_service_tier_to_standard() -> None:
    client = OpenAIClient(
        sdk_client=FakeSDK([_response({"candidates": []})]),
        attempts=1,
    )

    client.parse_structured_output(
        model="gpt-5.4",
        system_prompt="Extract signals.",
        input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
        response_model=SegmentSignalExtractionResult,
        context=_context(),
        service_tier="standard",
    )

    assert client.sdk_client.completions.requests[0]["service_tier"] == "default"


def test_responses_endpoint_uses_text_format_and_records_usage() -> None:
    recorder = RecordingUsageRecorder()
    client = OpenAIClient(
        sdk_client=FakeSDK([_responses_response({"candidates": []})]),
        usage_recorder=recorder,
        attempts=1,
    )

    result = client.parse_structured_output(
        model="gpt-5.5",
        system_prompt="Extract signals.",
        input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
        response_model=SegmentSignalExtractionResult,
        context=_context(),
        service_tier="standard",
        endpoint="responses",
    )

    assert result.candidates == []
    request = client.sdk_client.responses.requests[0]
    assert request["service_tier"] == "default"
    assert request["instructions"] == "Extract signals."
    assert request["text_format"] is SegmentSignalExtractionResult
    assert request["max_output_tokens"] > 0
    assert recorder.events[0].model == "gpt-5.5"
    assert recorder.events[0].input_tokens == 100
    assert recorder.events[0].output_tokens == 20


def test_invalid_service_tier_is_rejected_before_openai_call() -> None:
    client = OpenAIClient(
        sdk_client=FakeSDK([_response({"candidates": []})]),
        attempts=1,
    )

    with pytest.raises(ValueError, match="service_tier"):
        client.parse_structured_output(
            model="gpt-5.4",
            system_prompt="Extract signals.",
            input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
            response_model=SegmentSignalExtractionResult,
            context=_context(),
            service_tier="auto",
        )

    assert client.sdk_client.completions.requests == []


def test_invalid_endpoint_is_rejected_before_openai_call() -> None:
    client = OpenAIClient(
        sdk_client=FakeSDK([_response({"candidates": []})]),
        attempts=1,
    )

    with pytest.raises(ValueError, match="endpoint"):
        client.parse_structured_output(
            model="gpt-5.4",
            system_prompt="Extract signals.",
            input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
            response_model=SegmentSignalExtractionResult,
            context=_context(),
            endpoint="legacy",
        )

    assert client.sdk_client.completions.requests == []
    assert client.sdk_client.responses.requests == []


def test_failed_call_logs_sanitized_openai_metadata_without_transcript_text(caplog) -> None:
    class OpenAIInternalServerError(Exception):
        status_code = 500
        request_id = "req_sanitized"

    client = OpenAIClient(
        sdk_client=FakeSDK([OpenAIInternalServerError("SECRET TRANSCRIPT TEXT")]),
        attempts=1,
    )

    with caplog.at_level("WARNING"), pytest.raises(OpenAIInternalServerError):
        client.parse_structured_output(
            model="gpt-5.5",
            system_prompt="Extract signals.",
            input_payload={"text": "SECRET TRANSCRIPT TEXT"},
            response_model=SegmentSignalExtractionResult,
            context=_context(),
            service_tier="standard",
            endpoint="responses",
        )

    assert "request_id=req_sanitized" in caplog.text
    assert "status_code=500" in caplog.text
    assert "model=gpt-5.5" in caplog.text
    assert "endpoint=responses" in caplog.text
    assert "service_tier=standard" in caplog.text
    assert "api_service_tier=default" in caplog.text
    assert "agent_name=SignalExtractionAgent" in caplog.text
    assert "SECRET" not in caplog.text


def test_failed_chunk_call_records_sanitized_error_metadata_without_transcript_text() -> None:
    recorder = RecordingUsageRecorder()
    client = OpenAIClient(
        sdk_client=FakeSDK([RuntimeError("SECRET TRANSCRIPT TEXT")]),
        usage_recorder=recorder,
        attempts=1,
    )

    with pytest.raises(RuntimeError):
        client.parse_structured_output(
            model="gpt-5.4",
            system_prompt="Extract signals.",
            input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
            response_model=SegmentSignalExtractionResult,
            context=_context(),
        )

    event = recorder.events[0]
    assert event.status == "failed"
    assert event.error_type == "RuntimeError"
    assert "SECRET" not in event.model_dump_json()
    assert event.input_tokens == 0
    assert event.output_tokens == 0


def test_usage_recording_failure_does_not_retry_successful_openai_call() -> None:
    sdk = FakeSDK([_response({"candidates": []})])
    client = OpenAIClient(
        sdk_client=sdk,
        usage_recorder=FailingUsageRecorder(),
        attempts=3,
    )

    with pytest.raises(RuntimeError, match="usage store unavailable"):
        client.parse_structured_output(
            model="gpt-5.4",
            system_prompt="Extract signals.",
            input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
            response_model=SegmentSignalExtractionResult,
            context=_context(),
        )

    assert len(sdk.completions.requests) == 1


def test_authentication_error_is_recorded_without_retry() -> None:
    recorder = RecordingUsageRecorder()
    sdk = FakeSDK([AuthenticationError("invalid api key")])
    client = OpenAIClient(
        sdk_client=sdk,
        usage_recorder=recorder,
        attempts=3,
    )

    with pytest.raises(AuthenticationError):
        client.parse_structured_output(
            model="gpt-5.4",
            system_prompt="Extract signals.",
            input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
            response_model=SegmentSignalExtractionResult,
            context=_context(),
        )

    assert len(sdk.completions.requests) == 1
    assert recorder.events[0].status == "failed"
    assert recorder.events[0].error_type == "AuthenticationError"
    assert recorder.events[0].retry_count == 0


def test_multiple_chunks_create_multiple_usage_records() -> None:
    recorder = RecordingUsageRecorder()
    client = OpenAIClient(
        sdk_client=FakeSDK(
            [
                _response({"candidates": []}, prompt_tokens=50, completion_tokens=5),
                _response({"candidates": []}, prompt_tokens=60, completion_tokens=6),
            ]
        ),
        usage_recorder=recorder,
        attempts=1,
    )
    prepared = PreparedTranscript(
        transcript_id="call_sanitized",
        chunks=[
            TranscriptChunk(
                transcript_id="call_sanitized",
                chunk_id="call_sanitized_chunk_001",
                start_timestamp="00:01:00",
                end_timestamp="00:01:30",
                turns=[
                    TranscriptTurn(
                        sequence=1,
                        timestamp="00:01:00",
                        end_timestamp=None,
                        speaker="Advisor",
                        speaker_role="advisor",
                        text="I need stronger support.",
                    )
                ],
            ),
            TranscriptChunk(
                transcript_id="call_sanitized",
                chunk_id="call_sanitized_chunk_002",
                start_timestamp="00:02:00",
                end_timestamp="00:02:30",
                turns=[
                    TranscriptTurn(
                        sequence=2,
                        timestamp="00:02:00",
                        end_timestamp=None,
                        speaker="Advisor",
                        speaker_role="advisor",
                        text="The transition timing is a concern.",
                    )
                ],
            ),
        ],
    )

    candidates = SignalExtractionAgent(llm_client=client).run(prepared)

    assert candidates == []
    assert [event.chunk_id for event in recorder.events] == [
        "call_sanitized_chunk_001",
        "call_sanitized_chunk_002",
    ]


def test_consolidation_call_records_cross_segment_usage_context() -> None:
    recorder = RecordingUsageRecorder()
    client = OpenAIClient(
        sdk_client=FakeSDK(
            [
                _consolidation_response(
                    {
                        "ranked_signals": [
                            {
                                "source_candidate_id": "candidate_001",
                                "item_type": "driver",
                                "rank": 1,
                                "category": "Operational support",
                                "advisor_quote": "I need stronger support.",
                                "timestamp": "00:01:00",
                                "evidence_strength": "explicit",
                                "rationale": "The advisor states a support need.",
                            }
                        ]
                    },
                    prompt_tokens=80,
                    completion_tokens=10,
                )
            ]
        ),
        usage_recorder=recorder,
        attempts=1,
    )
    candidates = [
        CandidateSignal(
            transcript_id="call_sanitized",
            item_type="driver",
            category="Operational support",
            advisor_quote="I need stronger support.",
            timestamp="00:01:00",
            evidence_strength="explicit",
            rationale="The advisor states a support need.",
            source_chunk_id="call_sanitized_chunk_001",
        )
    ]

    ranked = ConsolidationRankingAgent(
        llm_client=client,
        pipeline_run_id="run_sanitized",
    ).run(candidates)

    assert len(ranked) == 1
    event = recorder.events[0]
    assert event.agent_name == "ConsolidationRankingAgent"
    assert event.pipeline_step == "consolidation_ranking"
    assert event.prompt_version == "consolidation_ranking_v1"
    assert event.model == "gpt-5.5"
    assert event.chunk_id is None
