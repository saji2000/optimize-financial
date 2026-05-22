from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Literal, Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.core.sentry import llm_observability_attributes, record_llm_observability
from app.llm.pricing import estimate_openai_cost_usd
from app.services.llm_usage_service import LLMUsageEventCreate


ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)
ServiceTier = Literal["flex", "standard"]
OpenAIEndpoint = Literal["chat_completions", "responses"]
DEFAULT_SERVICE_TIER: ServiceTier = "flex"
DEFAULT_OPENAI_ENDPOINT: OpenAIEndpoint = "chat_completions"
DEFAULT_RETRY_DELAY_SECONDS = 60.0
TRANSIENT_OPENAI_ERROR_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
    "RateLimitError",
}
LOGGER = logging.getLogger(__name__)


def get_openai_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def is_retryable_llm_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    if isinstance(status_code, int):
        return status_code == 429 or status_code >= 500
    return error.__class__.__name__ in TRANSIENT_OPENAI_ERROR_NAMES


class UsageRecorder(Protocol):
    def record(self, event: LLMUsageEventCreate) -> None:
        pass


class LLMCallContext(BaseModel):
    pipeline_run_id: str | None = None
    transcript_id: str
    chunk_id: str | None = None
    agent_name: str
    pipeline_step: str
    prompt_version: str


class OpenAIClient:
    def __init__(
        self,
        sdk_client: OpenAI | None = None,
        usage_recorder: UsageRecorder | None = None,
        attempts: int = 3,
        initial_retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
        sleep_func: Callable[[float], None] = time.sleep,
    ) -> None:
        if attempts <= 0:
            raise ValueError("attempts must be greater than zero")
        if initial_retry_delay_seconds < 0:
            raise ValueError("initial_retry_delay_seconds must be non-negative")

        self.sdk_client = sdk_client
        self.usage_recorder = usage_recorder
        self.attempts = attempts
        self.initial_retry_delay_seconds = initial_retry_delay_seconds
        self.sleep_func = sleep_func

    def parse_structured_output(
        self,
        *,
        model: str,
        system_prompt: str,
        input_payload: dict[str, Any],
        response_model: type[ResponseModelT],
        context: LLMCallContext,
        max_output_tokens: int = settings.openai_max_output_tokens,
        service_tier: ServiceTier = DEFAULT_SERVICE_TIER,
        endpoint: OpenAIEndpoint = DEFAULT_OPENAI_ENDPOINT,
    ) -> ResponseModelT:
        self._validate_service_tier(service_tier)
        self._validate_endpoint(endpoint)
        started_at = time.perf_counter()
        last_error: Exception | None = None
        last_input_tokens = 0
        last_output_tokens = 0
        final_attempt_index = 0

        for attempt_index in range(self.attempts):
            final_attempt_index = attempt_index
            try:
                response = self._create_structured_response(
                    model=model,
                    system_prompt=system_prompt,
                    input_payload=input_payload,
                    response_model=response_model,
                    max_output_tokens=max_output_tokens,
                    service_tier=service_tier,
                    endpoint=endpoint,
                )
                latency_ms = self._elapsed_ms(started_at)
                input_tokens, output_tokens = self._extract_token_usage(response)
                last_input_tokens = input_tokens
                last_output_tokens = output_tokens
                parsed = self._parse_response(response, response_model)
            except Exception as exc:
                last_error = exc
                self._log_openai_failure(
                    error=exc,
                    model=model,
                    endpoint=endpoint,
                    service_tier=service_tier,
                    context=context,
                    attempt_index=attempt_index,
                )
                if self._should_retry(exc) and attempt_index < self.attempts - 1:
                    self._sleep_before_retry(
                        attempt_index=attempt_index,
                        context=context,
                    )
                    continue
                break
            else:
                self._record_usage(
                    context=context,
                    model=model,
                    endpoint=endpoint,
                    service_tier=service_tier,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    retry_count=attempt_index,
                    status="success",
                    error_type=None,
                )
                return parsed

        latency_ms = self._elapsed_ms(started_at)
        error_type = self._sanitize_error_type(last_error)
        try:
            self._record_usage(
                context=context,
                model=model,
                endpoint=endpoint,
                service_tier=service_tier,
                input_tokens=last_input_tokens,
                output_tokens=last_output_tokens,
                latency_ms=latency_ms,
                retry_count=final_attempt_index,
                status="failed",
                error_type=error_type,
            )
        except Exception:
            if last_error is not None:
                raise last_error
            raise
        if last_error is None:
            raise RuntimeError("OpenAI structured output call failed without an exception")
        raise last_error

    def _create_structured_response(
        self,
        *,
        model: str,
        system_prompt: str,
        input_payload: dict[str, Any],
        response_model: type[ResponseModelT],
        max_output_tokens: int,
        service_tier: ServiceTier,
        endpoint: OpenAIEndpoint,
    ) -> Any:
        if endpoint == "responses":
            return self._create_responses_structured_response(
                model=model,
                system_prompt=system_prompt,
                input_payload=input_payload,
                response_model=response_model,
                max_output_tokens=max_output_tokens,
                service_tier=service_tier,
            )
        return self._create_chat_completions_structured_response(
            model=model,
            system_prompt=system_prompt,
            input_payload=input_payload,
            response_model=response_model,
            max_output_tokens=max_output_tokens,
            service_tier=service_tier,
        )

    def _create_chat_completions_structured_response(
        self,
        *,
        model: str,
        system_prompt: str,
        input_payload: dict[str, Any],
        response_model: type[ResponseModelT],
        max_output_tokens: int,
        service_tier: ServiceTier,
    ) -> Any:
        request: dict[str, Any] = {
            "model": model,
            "service_tier": self._api_service_tier(service_tier),
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(input_payload, ensure_ascii=False, separators=(",", ":")),
                },
            ],
            "response_format": response_model,
            "max_completion_tokens": max_output_tokens,
        }
        if settings.openai_temperature is not None:
            request["temperature"] = settings.openai_temperature

        sdk_client = self.sdk_client or get_openai_client()
        return sdk_client.beta.chat.completions.parse(**request)

    def _create_responses_structured_response(
        self,
        *,
        model: str,
        system_prompt: str,
        input_payload: dict[str, Any],
        response_model: type[ResponseModelT],
        max_output_tokens: int,
        service_tier: ServiceTier,
    ) -> Any:
        request: dict[str, Any] = {
            "model": model,
            "service_tier": self._api_service_tier(service_tier),
            "instructions": system_prompt,
            "input": json.dumps(input_payload, ensure_ascii=False, separators=(",", ":")),
            "text_format": response_model,
            "max_output_tokens": max_output_tokens,
        }
        if settings.openai_temperature is not None:
            request["temperature"] = settings.openai_temperature

        sdk_client = self.sdk_client or get_openai_client()
        return sdk_client.responses.parse(**request)

    def _parse_response(
        self, response: Any, response_model: type[ResponseModelT]
    ) -> ResponseModelT:
        parsed_response = getattr(response, "output_parsed", None)
        if parsed_response is not None:
            return response_model.model_validate(parsed_response)

        message = response.choices[0].message
        parsed = getattr(message, "parsed", None)
        if parsed is None:
            content = getattr(message, "content", "")
            return response_model.model_validate_json(content)
        return response_model.model_validate(parsed)

    def _extract_token_usage(self, response: Any) -> tuple[int, int]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return 0, 0

        input_tokens = self._read_int_attr(usage, "prompt_tokens", "input_tokens")
        output_tokens = self._read_int_attr(usage, "completion_tokens", "output_tokens")
        return input_tokens, output_tokens

    def _read_int_attr(self, item: Any, *names: str) -> int:
        for name in names:
            if isinstance(item, dict) and name in item:
                return int(item[name] or 0)
            value = getattr(item, name, None)
            if value is not None:
                return int(value)
        return 0

    def _record_usage(
        self,
        *,
        context: LLMCallContext,
        model: str,
        endpoint: OpenAIEndpoint,
        service_tier: ServiceTier,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        retry_count: int,
        status: str,
        error_type: str | None,
    ) -> None:
        input_cost, output_cost, total_cost = estimate_openai_cost_usd(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        record_llm_observability(
            attributes=llm_observability_attributes(
                pipeline_run_id=context.pipeline_run_id,
                transcript_id=context.transcript_id,
                chunk_id=context.chunk_id,
                agent_name=context.agent_name,
                pipeline_step=context.pipeline_step,
                model=model,
                prompt_version=context.prompt_version,
                endpoint=endpoint,
                service_tier=service_tier,
                status=status,
                error_type=error_type,
            ),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            retry_count=retry_count,
            cost_usd=total_cost,
        )
        if self.usage_recorder is None:
            return

        self.usage_recorder.record(
            LLMUsageEventCreate(
                pipeline_run_id=context.pipeline_run_id,
                transcript_id=context.transcript_id,
                chunk_id=context.chunk_id,
                agent_name=context.agent_name,
                pipeline_step=context.pipeline_step,
                model=model,
                prompt_version=context.prompt_version,
                pricing_version=settings.openai_pricing_version,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                estimated_input_cost_usd=input_cost,
                estimated_output_cost_usd=output_cost,
                estimated_total_cost_usd=total_cost,
                latency_ms=latency_ms,
                retry_count=retry_count,
                status=status,
                error_type=error_type,
            )
        )

    def _sanitize_error_type(self, error: Exception | None) -> str:
        if error is None:
            return "UnknownError"
        return error.__class__.__name__

    def _should_retry(self, error: Exception) -> bool:
        return is_retryable_llm_error(error)

    def _sleep_before_retry(
        self,
        *,
        attempt_index: int,
        context: LLMCallContext,
    ) -> None:
        delay_seconds = self._retry_delay_seconds(attempt_index)
        LOGGER.warning(
            "Delaying OpenAI retry: delay_seconds=%s agent_name=%s "
            "pipeline_step=%s transcript_id=%r chunk_id=%r next_attempt=%s/%s",
            delay_seconds,
            context.agent_name,
            context.pipeline_step,
            context.transcript_id,
            context.chunk_id,
            attempt_index + 2,
            self.attempts,
        )
        self.sleep_func(delay_seconds)

    def _retry_delay_seconds(self, attempt_index: int) -> float:
        return self.initial_retry_delay_seconds * (2 ** attempt_index)

    def _validate_service_tier(self, service_tier: str) -> None:
        if service_tier not in ("flex", "standard"):
            raise ValueError("service_tier must be 'flex' or 'standard'")

    def _validate_endpoint(self, endpoint: str) -> None:
        if endpoint not in ("chat_completions", "responses"):
            raise ValueError("endpoint must be 'chat_completions' or 'responses'")

    def _elapsed_ms(self, started_at: float) -> int:
        return max(0, int((time.perf_counter() - started_at) * 1000))

    def _log_openai_failure(
        self,
        *,
        error: Exception,
        model: str,
        endpoint: OpenAIEndpoint,
        service_tier: ServiceTier,
        context: LLMCallContext,
        attempt_index: int,
    ) -> None:
        LOGGER.warning(
            "OpenAI structured output call failed: error_type=%s status_code=%s "
            "request_id=%s model=%s endpoint=%s service_tier=%s agent_name=%s "
            "api_service_tier=%s pipeline_step=%s transcript_id=%r chunk_id=%r "
            "attempt=%s/%s retryable=%s",
            self._sanitize_error_type(error),
            self._status_code(error),
            self._request_id(error),
            model,
            endpoint,
            service_tier,
            context.agent_name,
            self._api_service_tier(service_tier),
            context.pipeline_step,
            context.transcript_id,
            context.chunk_id,
            attempt_index + 1,
            self.attempts,
            self._should_retry(error),
        )

    def _status_code(self, error: Exception) -> int | None:
        status_code = getattr(error, "status_code", None)
        return status_code if isinstance(status_code, int) else None

    def _request_id(self, error: Exception) -> str | None:
        request_id = getattr(error, "request_id", None) or getattr(error, "_request_id", None)
        if request_id:
            return str(request_id)

        response = getattr(error, "response", None)
        headers = getattr(response, "headers", None)
        if headers is not None:
            for name in ("x-request-id", "openai-request-id"):
                value = headers.get(name)
                if value:
                    return str(value)
        return None

    def _api_service_tier(self, service_tier: ServiceTier) -> str:
        if service_tier == "standard":
            return "default"
        return service_tier
