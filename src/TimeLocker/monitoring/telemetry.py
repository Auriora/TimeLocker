"""
PostHog/OpenTelemetry integration helpers.

This module centralises telemetry configuration so PostHog can be swapped out
without touching call sites. It uses OpenTelemetry SDK with OTLP/HTTP exporters
and provides a thin wrapper for enabling/disabling via environment variables.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, LogExporter
from opentelemetry.trace import Status, StatusCode

from .. import __version__

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://eu.i.posthog.com"
DEFAULT_SERVICE_NAME = "timelocker-cli"
DEFAULT_LOGS_ENDPOINT = "https://us.i.posthog.com/i/v1/logs"  # PostHog logs beta (US only as of 2025-11-22)


def _clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _normalize_base_endpoint(endpoint: str) -> str:
    """Ensure endpoint base omits OTLP resource paths; PostHog expects /ingest/otlp."""

    clean = endpoint.rstrip("/")
    for suffix in (
                "/v1/traces",
                "/v1/metrics",
                "/v1/logs",
                "/ingest/otlp/v1/traces",
                "/ingest/otlp/v1/metrics",
                "/otlp/v1/traces",
                "/otlp/v1/metrics",
    ):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]
            break
    return clean


@dataclass
class TelemetryConfig:
    """Configuration for telemetry exporters."""

    enabled: bool
    api_key: Optional[str]
    endpoint: str = DEFAULT_ENDPOINT
    logs_endpoint: str = DEFAULT_LOGS_ENDPOINT
    service_name: str = DEFAULT_SERVICE_NAME
    sample_ratio: float = 1.0

    @classmethod
    def from_env(cls) -> "TelemetryConfig":
        env_flag = os.getenv("TIMELOCKER_TELEMETRY_ENABLED", "auto")
        api_key = os.getenv("POSTHOG_API_KEY") or os.getenv("TIMELOCKER_POSTHOG_KEY")
        endpoint = _normalize_base_endpoint(os.getenv("POSTHOG_OTLP_ENDPOINT", DEFAULT_ENDPOINT))
        logs_endpoint = os.getenv("POSTHOG_OTLP_LOGS_ENDPOINT", DEFAULT_LOGS_ENDPOINT)
        sample_raw = os.getenv("TIMELOCKER_TELEMETRY_SAMPLE_RATIO", "1.0")
        try:
            sample_ratio = _clamp_ratio(float(sample_raw))
        except ValueError:
            sample_ratio = 1.0

        if env_flag.lower() == "false":
            enabled = False
        elif env_flag.lower() in {"true", "1", "yes", "on"}:
            enabled = True
        else:
            enabled = bool(api_key)

        return cls(
                enabled=enabled,
                api_key=api_key,
                endpoint=endpoint,
                logs_endpoint=logs_endpoint,
                sample_ratio=sample_ratio,
        )


class TelemetryHandle:
    """Lifecycle handle for telemetry providers."""

    def __init__(
            self,
            tracer_provider: TracerProvider,
            meter_provider: MeterProvider,
            logger_provider: LoggerProvider,
    ) -> None:
        self._tracer_provider = tracer_provider
        self._meter_provider = meter_provider
        self._logger_provider = logger_provider

    def shutdown(self) -> None:
        """Flush and shutdown providers safely."""
        try:
            self._tracer_provider.shutdown()
        except Exception as exc:  # pragma: no cover - best-effort shutdown
            logger.debug("Tracer provider shutdown failed: %s", exc)
        try:
            self._meter_provider.shutdown()
        except Exception as exc:  # pragma: no cover - best-effort shutdown
            logger.debug("Meter provider shutdown failed: %s", exc)
        try:
            self._logger_provider.shutdown()
        except Exception as exc:  # pragma: no cover - best-effort shutdown
            logger.debug("Logger provider shutdown failed: %s", exc)

    def __enter__(self) -> "TelemetryHandle":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.shutdown()


def _build_span_exporter(config: TelemetryConfig) -> SpanExporter:
    headers = {"Authorization": f"Bearer {config.api_key}"}
    return OTLPSpanExporter(endpoint=f"{config.endpoint}/otlp/v1/traces", headers=headers)


def _build_metric_exporter(config: TelemetryConfig) -> OTLPMetricExporter:
    headers = {"Authorization": f"Bearer {config.api_key}"}
    return OTLPMetricExporter(endpoint=f"{config.endpoint}/otlp/v1/metrics", headers=headers)


def _build_log_exporter(config: TelemetryConfig) -> LogExporter:
    headers = {"Authorization": f"Bearer {config.api_key}"}
    return OTLPLogExporter(endpoint=config.logs_endpoint, headers=headers)


def setup_telemetry(
        config: TelemetryConfig,
        span_exporter_factory: Optional[Callable[[TelemetryConfig], SpanExporter]] = None,
        metric_exporter_factory: Optional[Callable[[TelemetryConfig], OTLPMetricExporter]] = None,
        log_exporter_factory: Optional[Callable[[TelemetryConfig], LogExporter]] = None,
) -> Optional[TelemetryHandle]:
    """Initialise OpenTelemetry with OTLP exporters.

    Returns a :class:`TelemetryHandle` when telemetry is enabled; otherwise
    returns ``None`` so callers can remain simple and fail-open.
    """

    if not config.enabled:
        logger.debug("Telemetry disabled by configuration")
        return None
    if not config.api_key:
        logger.warning("Telemetry enabled but POSTHOG_API_KEY not provided; disabling")
        return None

    resource = Resource.create(
            {
                    "service.name":           config.service_name,
                    "service.version":        __version__,
                    "deployment.environment": os.getenv("TIMELOCKER_ENV", "unknown"),
            }
    )

    try:
        tracer_provider = TracerProvider(
                sampler=ParentBased(TraceIdRatioBased(config.sample_ratio)),
                resource=resource,
        )
        span_exporter_factory = span_exporter_factory or _build_span_exporter
        span_exporter = span_exporter_factory(config)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)

        metric_exporter_factory = metric_exporter_factory or _build_metric_exporter
        metric_reader = PeriodicExportingMetricReader(metric_exporter_factory(config))
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        log_exporter_factory = log_exporter_factory or _build_log_exporter
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter_factory(config)))
        # Set global logger provider
        from opentelemetry import _logs

        _logs.set_logger_provider(logger_provider)

        logger.info("Telemetry initialised with endpoint %s", config.endpoint)
        return TelemetryHandle(tracer_provider, meter_provider, logger_provider)
    except Exception as exc:
        logger.warning("Telemetry disabled due to exporter error: %s", exc)
        return None


def setup_telemetry_from_env() -> Optional[TelemetryHandle]:
    """Convenience wrapper using environment defaults."""

    config = TelemetryConfig.from_env()
    return setup_telemetry(config)


def record_exception(exc: BaseException) -> None:
    """Record an exception as a span and a log. Fail-open on exporter errors."""

    tracer = trace.get_tracer(DEFAULT_SERVICE_NAME)
    current_span = trace.get_current_span()

    try:
        if current_span.get_span_context().is_valid:
            span = current_span
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
        else:
            with tracer.start_as_current_span("uncaught.exception") as span:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
    except Exception:  # pragma: no cover
        logger.debug("Failed to record span for exception", exc_info=True)

    try:
        from opentelemetry import _logs

        logger_provider = _logs.get_logger_provider()
        if logger_provider:
            otel_logger = logger_provider.get_logger(DEFAULT_SERVICE_NAME)
            otel_logger.emit(
                    severity_text="ERROR",
                    body=f"Unhandled exception: {exc}",
                    attributes={"exception.type": type(exc).__name__, "exception.message": str(exc)},
            )
    except Exception:  # pragma: no cover
        logger.debug("Failed to emit OTEL log for exception", exc_info=True)
