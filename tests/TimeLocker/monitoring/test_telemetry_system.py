import os
import uuid

import pytest
from opentelemetry import metrics, trace

from TimeLocker.monitoring.telemetry import setup_telemetry_from_env

pytestmark = [pytest.mark.integration, pytest.mark.network]


def _get_api_key() -> str:
    return os.getenv("POSTHOG_API_KEY") or os.getenv("TIMELOCKER_POSTHOG_KEY", "")


@pytest.mark.timeout(20)
def test_posthog_otlp_exception_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """Send an exception as span+log to PostHog OTLP endpoints (requires API key)."""

    api_key = _get_api_key()
    if not api_key:
        pytest.skip("POSTHOG_API_KEY not configured for system telemetry test")

    # Force telemetry on with EU endpoint and full sampling
    monkeypatch.setenv("POSTHOG_API_KEY", api_key)
    monkeypatch.setenv("POSTHOG_OTLP_ENDPOINT", "https://eu.i.posthog.com")
    monkeypatch.setenv("TIMELOCKER_TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("TIMELOCKER_TELEMETRY_SAMPLE_RATIO", "1.0")

    handle = setup_telemetry_from_env()
    assert handle is not None, "Telemetry should be enabled when API key is present"

    test_id = str(uuid.uuid4())
    try:
        raise RuntimeError(f"synthetic system test exception {test_id}")
    except RuntimeError as exc:
        from TimeLocker.monitoring.telemetry import record_exception

        record_exception(exc)

    # Flush/close exporters
    handle.shutdown()
