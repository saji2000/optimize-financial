from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, nullcontext
from typing import Any

from app.core.config import settings


LOGGER = logging.getLogger(__name__)
SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "input_payload",
    "messages",
    "model_output",
    "password",
    "prompt",
    "raw_text",
    "system_prompt",
    "token",
    "transcript",
    "turns",
    "advisor_quote",
)
ALLOWLISTED_LOGGER_PREFIXES = (
    "app.llm.",
    "app.pipeline.",
    "app.workers.",
    "app.api.",
    "app.main",
)
OBSERVABILITY_MARKER = "optimize.sentry_observability"
REDACTED = "[Filtered]"

try:
    import sentry_sdk as _sentry_sdk
except ImportError:  # pragma: no cover - exercised when dependency is absent locally.
    _sentry_sdk = None


def configure_sentry(service_name: str) -> bool:
    if not settings.sentry_enabled or not settings.sentry_dsn:
        return False
    if _sentry_sdk is None:
        LOGGER.warning("Sentry is enabled but sentry-sdk is not installed.")
        return False

    integrations = _build_integrations()
    _sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.sentry_release or None,
        send_default_pii=False,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profile_session_sample_rate=settings.sentry_profile_session_sample_rate,
        enable_logs=settings.sentry_enable_logs,
        integrations=integrations,
        disabled_integrations=_build_disabled_integrations(),
        before_send=before_send,
        before_send_log=before_send_log,
        before_send_transaction=before_send_transaction,
        include_local_variables=False,
    )
    _sentry_sdk.set_tag("service", service_name)
    _sentry_sdk.set_tag("component", service_name)
    return True


def _build_integrations() -> list[Any]:
    integrations: list[Any] = []
    try:
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        return integrations

    integrations.append(
        StarletteIntegration(
            transaction_style="endpoint",
            failed_request_status_codes={range(500, 600)},
        )
    )
    integrations.append(
        FastApiIntegration(
            transaction_style="endpoint",
            failed_request_status_codes={range(500, 600)},
        )
    )
    integrations.append(CeleryIntegration())
    return integrations


def _build_disabled_integrations() -> list[Any]:
    try:
        from sentry_sdk.integrations.openai import OpenAIIntegration
    except ImportError:
        return []
    return [OpenAIIntegration]


def before_send(event: dict[str, Any], hint: dict[str, Any] | None) -> dict[str, Any] | None:
    scrubbed = _scrub_data(event)
    if not isinstance(scrubbed, dict):
        return None
    _scrub_breadcrumbs(scrubbed)
    return _scrub_exception_messages(scrubbed)


def before_send_log(log: dict[str, Any], hint: dict[str, Any] | None) -> dict[str, Any] | None:
    scrubbed = _scrub_data(log)
    if not isinstance(scrubbed, dict):
        return None

    attributes = _log_attributes(scrubbed)
    if attributes.get(OBSERVABILITY_MARKER) is True:
        return scrubbed

    severity = _log_severity(scrubbed)
    logger_name = str(attributes.get("code.logger.name") or attributes.get("logger") or "")
    if severity in ("warn", "warning", "error", "fatal") and logger_name.startswith(
        ALLOWLISTED_LOGGER_PREFIXES
    ):
        return scrubbed
    return None


def before_send_transaction(
    event: dict[str, Any],
    hint: dict[str, Any] | None,
) -> dict[str, Any] | None:
    transaction = str(event.get("transaction") or "")
    request = event.get("request") if isinstance(event.get("request"), dict) else {}
    url = str(request.get("url") or "")
    if transaction.endswith(" health") or transaction in {"health", "GET /health"}:
        return None
    if url.endswith("/health"):
        return None
    scrubbed = _scrub_data(event)
    return scrubbed if isinstance(scrubbed, dict) else None


def llm_observability_attributes(
    *,
    pipeline_run_id: str | None,
    transcript_id: str | None,
    chunk_id: str | None,
    agent_name: str,
    pipeline_step: str,
    model: str,
    prompt_version: str,
    endpoint: str,
    service_tier: str,
    status: str,
    error_type: str | None = None,
) -> dict[str, str | int | float | bool | None]:
    attributes: dict[str, str | int | float | bool | None] = {
        OBSERVABILITY_MARKER: True,
        "pipeline_run_id": pipeline_run_id,
        "transcript_id_hash": _hash_identifier(transcript_id),
        "chunk_id_hash": _hash_identifier(chunk_id),
        "agent_name": agent_name,
        "pipeline_step": pipeline_step,
        "model": model,
        "prompt_version": prompt_version,
        "endpoint": endpoint,
        "service_tier": service_tier,
        "status": status,
    }
    if error_type is not None:
        attributes["error_type"] = error_type
    return {key: value for key, value in attributes.items() if value is not None}


def pipeline_observability_attributes(
    *,
    pipeline_run_id: str | None,
    transcript_id: str | None,
    agent_name: str,
    pipeline_step: str,
    status: str,
    error_type: str | None = None,
) -> dict[str, str | bool | None]:
    attributes: dict[str, str | bool | None] = {
        OBSERVABILITY_MARKER: True,
        "pipeline_run_id": pipeline_run_id,
        "transcript_id_hash": _hash_identifier(transcript_id),
        "agent_name": agent_name,
        "pipeline_step": pipeline_step,
        "status": status,
    }
    if error_type is not None:
        attributes["error_type"] = error_type
    return {key: value for key, value in attributes.items() if value is not None}


def record_llm_observability(
    *,
    attributes: Mapping[str, str | int | float | bool | None],
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    retry_count: int,
    cost_usd: float,
) -> None:
    attrs = _compact_attributes(attributes)
    status = str(attrs.get("status") or "")
    _emit_metric("optimize.llm.calls", 1, attrs, metric_type="counter")
    _emit_metric("optimize.llm.latency_ms", latency_ms, attrs, metric_type="distribution")
    _emit_metric("optimize.llm.input_tokens", input_tokens, attrs, metric_type="distribution")
    _emit_metric("optimize.llm.output_tokens", output_tokens, attrs, metric_type="distribution")
    _emit_metric("optimize.llm.cost_usd", cost_usd, attrs, metric_type="distribution")
    _emit_metric("optimize.llm.retries", retry_count, attrs, metric_type="counter")
    if status == "failed":
        _emit_metric("optimize.llm.failures", 1, attrs, metric_type="counter")
    _safe_log(
        "optimize.llm.usage",
        level="error" if status == "failed" else "info",
        attributes={
            **attrs,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "retry_count": retry_count,
            "cost_usd": cost_usd,
        },
    )


@contextmanager
def pipeline_stage_span(
    *,
    pipeline_run_id: str | None,
    transcript_id: str,
    agent_name: str,
    pipeline_step: str,
) -> Iterator[None]:
    attributes = pipeline_observability_attributes(
        pipeline_run_id=pipeline_run_id,
        transcript_id=transcript_id,
        agent_name=agent_name,
        pipeline_step=pipeline_step,
        status="running",
    )
    started_at = time.perf_counter()
    span_context = _start_span("pipeline.stage", pipeline_step, attributes)
    error_type: str | None = None
    status = "success"
    try:
        with span_context:
            yield
    except Exception as exc:
        status = "failed"
        error_type = exc.__class__.__name__
        raise
    finally:
        duration_ms = max(0, int((time.perf_counter() - started_at) * 1000))
        outcome_attrs = pipeline_observability_attributes(
            pipeline_run_id=pipeline_run_id,
            transcript_id=transcript_id,
            agent_name=agent_name,
            pipeline_step=pipeline_step,
            status=status,
            error_type=error_type,
        )
        _emit_metric(
            "optimize.pipeline.stage.duration_ms",
            duration_ms,
            outcome_attrs,
            metric_type="distribution",
        )
        _emit_metric("optimize.pipeline.stage.outcomes", 1, outcome_attrs, metric_type="counter")
        if status == "failed":
            _emit_metric("optimize.pipeline.stage.failures", 1, outcome_attrs, metric_type="counter")
        _safe_log(
            "optimize.pipeline.stage",
            level="error" if status == "failed" else "info",
            attributes={**outcome_attrs, "duration_ms": duration_ms},
        )


def capture_sanitized_exception(
    error: Exception,
    *,
    pipeline_run_id: str | None,
    transcript_id: str | None,
    agent_name: str,
    pipeline_step: str,
) -> None:
    if _sentry_sdk is None:
        return
    attributes = pipeline_observability_attributes(
        pipeline_run_id=pipeline_run_id,
        transcript_id=transcript_id,
        agent_name=agent_name,
        pipeline_step=pipeline_step,
        status="failed",
        error_type=error.__class__.__name__,
    )
    with _push_scope() as scope:
        _set_scope_attributes(scope, attributes)
        _sentry_sdk.capture_exception(error)


def _start_span(
    op: str,
    name: str,
    attributes: Mapping[str, str | int | float | bool | None],
) -> Any:
    if _sentry_sdk is None:
        return nullcontext()
    try:
        span = _sentry_sdk.start_span(op=op, name=name)
        for key, value in _compact_attributes(attributes).items():
            if hasattr(span, "set_attribute"):
                span.set_attribute(key, value)
            elif hasattr(span, "set_data"):
                span.set_data(key, value)
        return span
    except Exception:
        return nullcontext()


def _emit_metric(
    name: str,
    value: int | float,
    attributes: Mapping[str, str | int | float | bool | None],
    *,
    metric_type: str,
) -> None:
    if _sentry_sdk is None:
        return
    metrics = getattr(_sentry_sdk, "metrics", None)
    if metrics is None:
        return

    tags = _string_tags(attributes)
    try:
        if metric_type == "counter":
            increment = getattr(metrics, "incr", None) or getattr(metrics, "increment", None)
            if increment is not None:
                increment(name, value, tags=tags)
        else:
            distribution = getattr(metrics, "distribution", None)
            if distribution is not None:
                distribution(name, value, tags=tags)
    except Exception:
        LOGGER.debug("Failed to emit Sentry metric %s", name, exc_info=False)


def _safe_log(
    message: str,
    *,
    level: str,
    attributes: Mapping[str, str | int | float | bool | None],
) -> None:
    if _sentry_sdk is None:
        return
    attrs = _compact_attributes(attributes)
    logger = getattr(_sentry_sdk, "logger", None)
    log_method = getattr(logger, level, None) if logger is not None else None
    if log_method is not None:
        try:
            log_method(message, attributes=attrs)
            return
        except Exception:
            pass

    log_level = logging.ERROR if level == "error" else logging.INFO
    LOGGER.log(log_level, "%s %s", message, attrs)


def _push_scope() -> Any:
    if _sentry_sdk is None:
        return nullcontext()
    push_scope = getattr(_sentry_sdk, "push_scope", None)
    if push_scope is not None:
        return push_scope()
    return nullcontext()


def _set_scope_attributes(scope: Any, attributes: Mapping[str, str | int | float | bool]) -> None:
    for key, value in attributes.items():
        if hasattr(scope, "set_tag"):
            scope.set_tag(key, value)
    if hasattr(scope, "set_context"):
        scope.set_context("optimize", dict(attributes))


def _compact_attributes(
    attributes: Mapping[str, str | int | float | bool | None],
) -> dict[str, str | int | float | bool]:
    return {key: value for key, value in attributes.items() if value is not None}


def _string_tags(attributes: Mapping[str, str | int | float | bool | None]) -> dict[str, str]:
    return {
        key: str(value)
        for key, value in attributes.items()
        if value is not None and not isinstance(value, float)
    }


def _scrub_data(value: Any) -> Any:
    if isinstance(value, dict):
        scrubbed: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                scrubbed[key] = REDACTED
            elif key_text == "request" and isinstance(item, dict):
                scrubbed[key] = _scrub_request(item)
            else:
                scrubbed[key] = _scrub_data(item)
        return scrubbed
    if isinstance(value, list):
        return [_scrub_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_data(item) for item in value)
    return value


def _scrub_request(request: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"method", "url", "env"}
    scrubbed = {key: _scrub_data(value) for key, value in request.items() if key in allowed_keys}
    if "url" in scrubbed and isinstance(scrubbed["url"], str):
        scrubbed["url"] = scrubbed["url"].split("?", 1)[0]
    if "env" in scrubbed and isinstance(scrubbed["env"], dict):
        scrubbed["env"] = {
            key: value
            for key, value in scrubbed["env"].items()
            if not _is_sensitive_key(str(key))
        }
    return scrubbed


def _scrub_exception_messages(event: dict[str, Any]) -> dict[str, Any]:
    exception = event.get("exception")
    if not isinstance(exception, dict):
        return event
    values = exception.get("values")
    if not isinstance(values, list):
        return event
    for item in values:
        if isinstance(item, dict) and "value" in item:
            item["value"] = REDACTED
    return event


def _scrub_breadcrumbs(event: dict[str, Any]) -> None:
    breadcrumbs = event.get("breadcrumbs")
    if not isinstance(breadcrumbs, dict):
        return
    values = breadcrumbs.get("values")
    if not isinstance(values, list):
        return
    for item in values:
        if not isinstance(item, dict):
            continue
        if "message" in item:
            item["message"] = REDACTED
        if "data" in item:
            item["data"] = _scrub_data(item["data"])


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _log_attributes(log: dict[str, Any]) -> dict[str, Any]:
    attributes = log.get("attributes")
    return attributes if isinstance(attributes, dict) else {}


def _log_severity(log: dict[str, Any]) -> str:
    for key in ("severity_text", "level", "levelname"):
        value = log.get(key)
        if value:
            return str(value).lower()
    attributes = _log_attributes(log)
    for key in ("sentry.severity_text", "level", "levelname"):
        value = attributes.get(key)
        if value:
            return str(value).lower()
    return ""


def _hash_identifier(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
