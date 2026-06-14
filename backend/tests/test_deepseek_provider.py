import json
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.llm.openai_client import LLMCallContext, OpenAIClient
from app.llm.structured_outputs import SegmentSignalExtractionResult


class RecordingUsageRecorder:
    def __init__(self) -> None:
        self.events = []

    def record(self, event) -> None:
        self.events.append(event)


class FakeDeepSeekChatCompletions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[dict] = []

    def create(self, **request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeDeepSeekSDK:
    """Mimics the OpenAI SDK pointed at DeepSeek: only chat.completions.create."""

    def __init__(self, responses: list[object]) -> None:
        self.completions = FakeDeepSeekChatCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def _deepseek_response(
    payload: dict,
    prompt_tokens: int = 100,
    completion_tokens: int = 20,
    cache_hit_tokens: int = 0,
):
    # DeepSeek JSON mode returns the JSON in message.content (no .parsed).
    content = json.dumps(payload)
    usage_kwargs: dict = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }
    if cache_hit_tokens:
        usage_kwargs["prompt_cache_hit_tokens"] = cache_hit_tokens
        usage_kwargs["prompt_cache_miss_tokens"] = prompt_tokens - cache_hit_tokens
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(**usage_kwargs),
    )


def _context() -> LLMCallContext:
    return LLMCallContext(
        pipeline_run_id="run_sanitized",
        transcript_id="call_sanitized",
        chunk_id="call_sanitized_chunk_001",
        agent_name="SignalExtractionAgent",
        pipeline_step="segment_signal_extraction",
        prompt_version="signal_extraction_v1",
    )


def _client(responses, **kwargs):
    return OpenAIClient(
        sdk_client=FakeDeepSeekSDK(responses),
        provider="deepseek",
        attempts=1,
        **kwargs,
    )


def test_deepseek_uses_chat_completions_json_mode_without_service_tier() -> None:
    recorder = RecordingUsageRecorder()
    client = _client([_deepseek_response({"candidates": []})], usage_recorder=recorder)

    result = client.parse_structured_output(
        model="deepseek-v4-flash",
        system_prompt="Extract signals.",
        input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
        response_model=SegmentSignalExtractionResult,
        context=_context(),
        # Agents 3/4 pass endpoint="responses"; DeepSeek must still use chat completions.
        endpoint="responses",
    )

    assert result.candidates == []
    request = client.sdk_client.completions.requests[0]
    assert "service_tier" not in request
    assert request["response_format"] == {"type": "json_object"}
    assert request["max_tokens"] > 0
    assert request["model"] == "deepseek-v4-flash"
    # Schema is injected into the system prompt (JSON mode requires "json" + schema).
    system_content = request["messages"][0]["content"]
    assert "json" in system_content.lower()
    assert "candidates" in system_content


def test_deepseek_records_usage_with_deepseek_pricing() -> None:
    recorder = RecordingUsageRecorder()
    client = _client([_deepseek_response({"candidates": []})], usage_recorder=recorder)

    client.parse_structured_output(
        model="deepseek-v4-flash",
        system_prompt="Extract signals.",
        input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
        response_model=SegmentSignalExtractionResult,
        context=_context(),
    )

    event = recorder.events[0]
    assert event.model == "deepseek-v4-flash"
    assert event.input_tokens == 100
    assert event.output_tokens == 20
    assert event.total_tokens == 120
    # deepseek-v4-flash rates: input 0.14, output 0.28 per 1M tokens.
    assert event.estimated_input_cost_usd == pytest.approx(100 / 1_000_000 * 0.14)
    assert event.estimated_output_cost_usd == pytest.approx(20 / 1_000_000 * 0.28)
    assert event.estimated_total_cost_usd == pytest.approx(0.000019600)
    assert event.pricing_version == settings.openai_pricing_version
    assert event.status == "success"


def test_deepseek_cache_hit_tokens_lower_input_cost() -> None:
    recorder = RecordingUsageRecorder()
    client = _client(
        [
            _deepseek_response(
                {"candidates": []},
                prompt_tokens=1000,
                completion_tokens=100,
                cache_hit_tokens=800,
            )
        ],
        usage_recorder=recorder,
    )

    client.parse_structured_output(
        model="deepseek-v4-flash",
        system_prompt="Extract signals.",
        input_payload={"chunk_id": "call_sanitized_chunk_001", "turns": []},
        response_model=SegmentSignalExtractionResult,
        context=_context(),
    )

    event = recorder.events[0]
    assert event.input_tokens == 1000
    # 200 cache-miss tokens @ 0.14 + 800 cache-hit tokens @ 0.0028 per 1M.
    expected_input = 200 / 1_000_000 * 0.14 + 800 / 1_000_000 * 0.0028
    assert event.estimated_input_cost_usd == pytest.approx(expected_input)
    assert event.estimated_output_cost_usd == pytest.approx(100 / 1_000_000 * 0.28)
    # Cheaper than billing all 1000 input tokens at the cache-miss rate.
    assert event.estimated_input_cost_usd < 1000 / 1_000_000 * 0.14


def test_deepseek_pro_cost_is_recorded() -> None:
    recorder = RecordingUsageRecorder()
    client = _client(
        [_deepseek_response({"candidates": []}, prompt_tokens=1000, completion_tokens=500)],
        usage_recorder=recorder,
    )

    client.parse_structured_output(
        model="deepseek-v4-pro",
        system_prompt="Rank signals.",
        input_payload={"candidates": []},
        response_model=SegmentSignalExtractionResult,
        context=_context(),
        endpoint="responses",
    )

    event = recorder.events[0]
    assert event.model == "deepseek-v4-pro"
    # deepseek-v4-pro rates: input 0.435, output 0.87 per 1M tokens.
    assert event.estimated_input_cost_usd == pytest.approx(1000 / 1_000_000 * 0.435)
    assert event.estimated_output_cost_usd == pytest.approx(500 / 1_000_000 * 0.87)


def test_deepseek_reports_chat_completions_endpoint_in_observability(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        "app.llm.openai_client.record_llm_observability",
        lambda **kwargs: calls.append(kwargs),
    )
    client = _client([_deepseek_response({"candidates": []})])

    client.parse_structured_output(
        model="deepseek-v4-pro",
        system_prompt="Validate signals.",
        input_payload={"raw_text": "SECRET TRANSCRIPT TEXT"},
        response_model=SegmentSignalExtractionResult,
        context=_context(),
        endpoint="responses",
    )

    assert len(calls) == 1
    attributes = calls[0]["attributes"]
    assert attributes["endpoint"] == "chat_completions"
    assert "SECRET" not in str(calls[0])
