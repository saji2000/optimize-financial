from __future__ import annotations

from app.core import sentry as sentry_module
from app.core.config import settings


class FakeSentrySDK:
    def __init__(self) -> None:
        self.init_kwargs = None
        self.tags = {}

    def init(self, **kwargs):
        self.init_kwargs = kwargs

    def set_tag(self, key, value):
        self.tags[key] = value


def test_no_dsn_disables_initialization_cleanly(monkeypatch) -> None:
    fake = FakeSentrySDK()
    monkeypatch.setattr(sentry_module, "_sentry_sdk", fake)
    monkeypatch.setattr(settings, "sentry_enabled", True)
    monkeypatch.setattr(settings, "sentry_dsn", "")

    initialized = sentry_module.configure_sentry(service_name="backend")

    assert initialized is False
    assert fake.init_kwargs is None


def test_dsn_initializes_with_pii_disabled(monkeypatch) -> None:
    fake = FakeSentrySDK()
    monkeypatch.setattr(sentry_module, "_sentry_sdk", fake)
    monkeypatch.setattr(sentry_module, "_build_integrations", lambda: [])
    monkeypatch.setattr(settings, "sentry_enabled", True)
    monkeypatch.setattr(settings, "sentry_dsn", "https://public@example.invalid/1")
    monkeypatch.setattr(settings, "sentry_environment", "test")
    monkeypatch.setattr(settings, "sentry_release", "backend@test")

    initialized = sentry_module.configure_sentry(service_name="backend")

    assert initialized is True
    assert fake.init_kwargs["send_default_pii"] is False
    assert fake.init_kwargs["include_local_variables"] is False
    assert fake.init_kwargs["enable_logs"] is True
    assert "disabled_integrations" in fake.init_kwargs
    assert fake.init_kwargs["environment"] == "test"
    assert fake.init_kwargs["release"] == "backend@test"
    assert fake.tags["service"] == "backend"


def test_health_transactions_are_dropped() -> None:
    assert sentry_module.before_send_transaction({"transaction": "GET /health"}, {}) is None
    assert (
        sentry_module.before_send_transaction(
            {"transaction": "health", "request": {"url": "http://testserver/health"}},
            {},
        )
        is None
    )


def test_sensitive_fields_are_scrubbed_from_events() -> None:
    event = {
        "request": {
            "method": "POST",
            "url": "http://testserver/transcripts",
            "headers": {"Authorization": "Bearer secret"},
            "data": {"raw_text": "SECRET TRANSCRIPT TEXT"},
        },
        "extra": {
            "messages": ["SECRET TRANSCRIPT TEXT"],
            "advisor_quote": "SECRET QUOTE",
            "safe": "ok",
        },
        "exception": {"values": [{"type": "RuntimeError", "value": "SECRET TRANSCRIPT TEXT"}]},
    }

    scrubbed = sentry_module.before_send(event, {})

    assert scrubbed is not None
    assert scrubbed["request"] == {"method": "POST", "url": "http://testserver/transcripts"}
    assert scrubbed["extra"]["messages"] == sentry_module.REDACTED
    assert scrubbed["extra"]["advisor_quote"] == sentry_module.REDACTED
    assert scrubbed["extra"]["safe"] == "ok"
    assert scrubbed["exception"]["values"][0]["value"] == sentry_module.REDACTED


def test_sensitive_fields_are_scrubbed_from_allowlisted_logs() -> None:
    log = {
        "severity_text": "warning",
        "body": "OpenAI structured output call failed",
        "attributes": {
            "code.logger.name": "app.llm.openai_client",
            "raw_text": "SECRET TRANSCRIPT TEXT",
            "prompt": "SECRET PROMPT",
            "model": "gpt-5.4",
        },
    }

    scrubbed = sentry_module.before_send_log(log, {})

    assert scrubbed is not None
    assert scrubbed["attributes"]["raw_text"] == sentry_module.REDACTED
    assert scrubbed["attributes"]["prompt"] == sentry_module.REDACTED
    assert scrubbed["attributes"]["model"] == "gpt-5.4"


def test_general_info_logs_are_dropped_unless_explicit_observability_helper() -> None:
    assert sentry_module.before_send_log({"severity_text": "info", "attributes": {}}, {}) is None

    helper_log = {
        "severity_text": "info",
        "attributes": {sentry_module.OBSERVABILITY_MARKER: True, "pipeline_step": "test"},
    }

    assert sentry_module.before_send_log(helper_log, {}) == helper_log
