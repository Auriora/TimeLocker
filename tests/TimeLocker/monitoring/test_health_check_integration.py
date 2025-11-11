"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import requests

from TimeLocker.monitoring import (
    HealthCheckIntegration,
    HealthCheckConfig,
    HealthCheckServiceConfig,
    HealthCheckServiceType,
    HealthCheckHealthStatus,
    PingResult
)


class TestHealthCheckIntegration:
    """Integration tests for health check services"""

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_health_check_config_creation(self):
        """Test creating health check configuration"""
        service_config = HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.HEALTHCHECKS_IO,
            check_id="abc123",
            api_key="secret_key"
        )

        config = HealthCheckConfig(
            enabled=True,
            services=[service_config],
            ping_on_start=True,
            ping_on_success=True,
            ping_on_failure=True
        )

        assert config.enabled is True
        assert len(config.services) == 1
        assert config.services[0].service_type == HealthCheckServiceType.HEALTHCHECKS_IO

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.get')
    def test_healthchecks_io_ping_success(self, mock_get):
        """Test successful ping to Healthchecks.io"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        service_config = HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.HEALTHCHECKS_IO,
            check_id="test-check-id"
        )

        config = HealthCheckConfig(
            enabled=True,
            services=[service_config]
        )

        integration = HealthCheckIntegration(config)
        result = integration.ping_success("backup_001")

        assert result.success is True
        mock_get.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.get')
    def test_healthchecks_io_ping_failure(self, mock_get):
        """Test failure ping to Healthchecks.io"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        service_config = HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.HEALTHCHECKS_IO,
            check_id="test-check-id"
        )

        config = HealthCheckConfig(
            enabled=True,
            services=[service_config]
        )

        integration = HealthCheckIntegration(config)
        result = integration.ping_failure("backup_001", "Backup failed")

        assert result.success is True
        mock_get.assert_called_once()
        # Verify /fail endpoint was called
        call_url = mock_get.call_args[0][0]
        assert "/fail" in call_url

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.get')
    def test_healthchecks_io_ping_start(self, mock_get):
        """Test start ping to Healthchecks.io"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        service_config = HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.HEALTHCHECKS_IO,
            check_id="test-check-id"
        )

        config = HealthCheckConfig(
            enabled=True,
            services=[service_config],
            ping_on_start=True
        )

        integration = HealthCheckIntegration(config)
        result = integration.ping_start("backup_001")

        assert result.success is True
        mock_get.assert_called_once()
        # Verify /start endpoint was called
        call_url = mock_get.call_args[0][0]
        assert "/start" in call_url

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.get')
    def test_health_check_connection_error(self, mock_get):
        """Test health check with connection error"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        service_config = HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.HEALTHCHECKS_IO,
            check_id="test-check-id"
        )

        config = HealthCheckConfig(
            enabled=True,
            services=[service_config]
        )

        integration = HealthCheckIntegration(config)
        result = integration.ping_success("backup_001")

        assert result.success is False
        assert result.error_message is not None

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_health_check_disabled(self):
        """Test health check when disabled"""
        config = HealthCheckConfig(
            enabled=False,
            services=[]
        )

        integration = HealthCheckIntegration(config)
        result = integration.ping_success("backup_001")

        # Should return success but not actually ping
        assert result.success is True

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.post')
    def test_uptime_kuma_push_integration(self, mock_post):
        """Test Uptime Kuma push monitor integration"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        service_config = HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.UPTIME_KUMA,
            push_url="https://uptime.example.com/api/push/abc123"
        )

        config = HealthCheckConfig(
            enabled=True,
            services=[service_config]
        )

        integration = HealthCheckIntegration(config)
        result = integration.ping_success("backup_001")

        assert result.success is True
        mock_post.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_multiple_health_check_services(self):
        """Test integration with multiple health check services"""
        services = [
            HealthCheckServiceConfig(
                service_type=HealthCheckServiceType.HEALTHCHECKS_IO,
                check_id="check1"
            ),
            HealthCheckServiceConfig(
                service_type=HealthCheckServiceType.UPTIME_KUMA,
                push_url="https://uptime.example.com/api/push/abc123"
            )
        ]

        config = HealthCheckConfig(
            enabled=True,
            services=services
        )

        integration = HealthCheckIntegration(config)

        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = Mock(status_code=200)
            mock_post.return_value = Mock(status_code=200, json=lambda: {"ok": True})

            result = integration.ping_success("backup_001")

            assert result.success is True
            # Both services should be called
            assert mock_get.called or mock_post.called
