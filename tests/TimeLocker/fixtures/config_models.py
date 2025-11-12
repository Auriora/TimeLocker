"""
Configuration model fixtures for tests.

This module provides pytest fixtures for creating valid configuration objects
with correct constructor parameters that match the actual model signatures.
"""

import pytest
from TimeLocker.monitoring import (
    HealthCheckServiceConfig,
    HealthCheckServiceType,
    WebhookConfig,
    PayloadFormat
)


@pytest.fixture
def health_check_service_config() -> HealthCheckServiceConfig:
    """
    Create a valid HealthCheckServiceConfig for testing.
    
    Based on the actual constructor in health_check_integration.py:
    - service_type: HealthCheckServiceType (required)
    - enabled: bool = True
    - ping_url: str = ""
    - api_key: Optional[str] = None
    - check_uuid: Optional[str] = None
    - timeout: int = 10
    - custom_headers: Dict[str, str] = field(default_factory=dict)
    - verify_ssl: bool = True
    
    Note: Tests were incorrectly using 'check_id' parameter which doesn't exist.
    The correct parameter is 'check_uuid'.
    
    Returns:
        HealthCheckServiceConfig: A valid configuration object for testing
    """
    return HealthCheckServiceConfig(
        service_type=HealthCheckServiceType.HEALTHCHECKS_IO,
        enabled=True,
        ping_url="https://hc-ping.com/test-uuid",
        api_key="test-api-key",
        check_uuid="test-uuid",
        timeout=10,
        custom_headers={},
        verify_ssl=True
    )


@pytest.fixture
def webhook_config() -> WebhookConfig:
    """
    Create a valid WebhookConfig for testing.
    
    Based on the actual constructor in webhook_handler.py:
    - enabled: bool = False
    - url: str = ""
    - payload_format: PayloadFormat = PayloadFormat.JSON
    - custom_headers: Dict[str, str] = field(default_factory=dict)
    - verify_ssl: bool = True
    - timeout: int = 10
    - max_retries: int = 3
    - retry_delay: float = 1.0
    - retry_backoff_multiplier: float = 2.0
    - include_metadata: bool = True
    - include_progress: bool = False
    
    Note: Tests were incorrectly using 'events' parameter which doesn't exist.
    Event filtering is handled by the WebhookHandler, not the config.
    
    Returns:
        WebhookConfig: A valid configuration object for testing
    """
    return WebhookConfig(
        enabled=True,
        url="https://example.com/webhook",
        payload_format=PayloadFormat.JSON,
        custom_headers={"Content-Type": "application/json"},
        verify_ssl=True,
        timeout=10,
        max_retries=3,
        retry_delay=1.0,
        retry_backoff_multiplier=2.0,
        include_metadata=True,
        include_progress=False
    )
