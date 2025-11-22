import os

import pytest
from opentelemetry.sdk.metrics.export import MetricExportResult, MetricExporter
from opentelemetry.sdk.trace.export import SpanExportResult, SpanExporter

from TimeLocker.monitoring.telemetry import (
    TelemetryConfig,
    TelemetryHandle,
    setup_telemetry,
)


class DummySpanExporter(SpanExporter):
    def __init__(self) -> None:
        self.shutdown_called = False

    def export(self, spans):  # type: ignore[override]
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:  # type: ignore[override]
        self.shutdown_called = True


class DummyMetricExporter(MetricExporter):
    def __init__(self) -> None:
        self.shutdown_called = False
        self._preferred_temporality = {}
        self._preferred_aggregation = {}

    def export(self, metrics_data):  # type: ignore[override]
        return MetricExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 10000) -> bool:  # type: ignore[override]
        return True

    def shutdown(self, *_, **__) -> None:  # type: ignore[override]
        self.shutdown_called = True


def test_config_disabled_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    monkeypatch.delenv("TIMELOCKER_TELEMETRY_ENABLED", raising=False)
    config = TelemetryConfig.from_env()
    assert config.enabled is False


def test_config_enabled_when_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMELOCKER_TELEMETRY_ENABLED", "true")
    config = TelemetryConfig.from_env()
    assert config.enabled is True


def test_endpoint_defaults_to_eu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTHOG_OTLP_ENDPOINT", raising=False)
    config = TelemetryConfig.from_env()
    assert config.endpoint == "https://eu.i.posthog.com"


def test_setup_telemetry_uses_custom_exporters(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure env does not influence this explicit config
    for key in ("POSTHOG_API_KEY", "TIMELOCKER_TELEMETRY_ENABLED"):
        monkeypatch.delenv(key, raising=False)

    span_exporter = DummySpanExporter()
    metric_exporter = DummyMetricExporter()

    config = TelemetryConfig(
            enabled=True,
            api_key="test-key",
            endpoint="https://eu.i.posthog.com",
    )

    handle = setup_telemetry(
            config,
            span_exporter_factory=lambda _: span_exporter,
            metric_exporter_factory=lambda _: metric_exporter,
    )

    assert isinstance(handle, TelemetryHandle)
    handle.shutdown()
    assert span_exporter.shutdown_called is True
    assert metric_exporter.shutdown_called is True


def test_sample_ratio_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMELOCKER_TELEMETRY_SAMPLE_RATIO", "2.5")
    monkeypatch.setenv("TIMELOCKER_TELEMETRY_ENABLED", "true")
    config = TelemetryConfig.from_env()
    assert config.sample_ratio == 1.0
