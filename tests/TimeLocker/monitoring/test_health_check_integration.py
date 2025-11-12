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
from pathlib import Path
import tempfile
import requests

from TimeLocker.monitoring import (
    HealthCheckIntegration,
    HealthCheckConfig,
    HealthCheckServiceConfig,
    HealthCheckServiceType,
    HealthStatus,
    PingResult
)
from tests.TimeLocker.fixtures.config_models import health_check_service_config


class TestHealthCheckIntegration:
    """Integration tests for health check services"""

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_health_check_config_creation(self, health_check_service_config):
        """Test creating health check configuration"""
        service_config = health_check_service_config

        config = HealthCheckConfig(
            enabled=True,
            services={"test_service": service_config},
            ping_on_backup_start=True,
            ping_on_backup_success=True,
            ping_on_backup_failure=True
        )

        assert config.enabled is True
        assert len(config.services) == 1
        assert config.services["test_service"].service_type == HealthCheckServiceType.HEALTHCHECKS_IO

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_healthchecks_io_ping_success(self, mock_post, health_check_service_config, tmp_path):
        """Test successful ping to Healthchecks.io"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Create integration with temp config dir
        integration = HealthCheckIntegration(config_dir=tmp_path)
        
        # Add service configuration
        integration.add_service("test_service", health_check_service_config)
        integration.config.enabled = True
        integration.config.ping_on_backup_success = True

        # Test notify backup success
        results = integration.notify_backup_success("backup_001")

        assert "test_service" in results
        assert results["test_service"].success is True
        mock_post.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_healthchecks_io_ping_failure(self, mock_post, health_check_service_config, tmp_path):
        """Test failure ping to Healthchecks.io"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Create integration with temp config dir
        integration = HealthCheckIntegration(config_dir=tmp_path)
        
        # Add service configuration
        integration.add_service("test_service", health_check_service_config)
        integration.config.enabled = True
        integration.config.ping_on_backup_failure = True

        # Test notify backup failure
        results = integration.notify_backup_failure("backup_001", "Backup failed")

        assert "test_service" in results
        assert results["test_service"].success is True
        mock_post.assert_called_once()
        # Verify /fail endpoint was called
        call_url = mock_post.call_args[0][0]
        assert "/fail" in call_url

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_healthchecks_io_ping_start(self, mock_post, health_check_service_config, tmp_path):
        """Test start ping to Healthchecks.io"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Create integration with temp config dir
        integration = HealthCheckIntegration(config_dir=tmp_path)
        
        # Add service configuration
        integration.add_service("test_service", health_check_service_config)
        integration.config.enabled = True
        integration.config.ping_on_backup_start = True

        # Test notify backup start
        results = integration.notify_backup_start("backup_001")

        assert "test_service" in results
        assert results["test_service"].success is True
        mock_post.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_health_check_connection_error(self, mock_post, health_check_service_config, tmp_path):
        """Test health check with connection error"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        # Create integration with temp config dir
        integration = HealthCheckIntegration(config_dir=tmp_path)
        
        # Add service configuration
        integration.add_service("test_service", health_check_service_config)
        integration.config.enabled = True
        integration.config.ping_on_backup_success = True

        # Test notify backup success with connection error
        results = integration.notify_backup_success("backup_001")

        assert "test_service" in results
        assert results["test_service"].success is False
        assert results["test_service"].error_message is not None

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_health_check_disabled(self, tmp_path):
        """Test health check when disabled"""
        # Create integration with temp config dir
        integration = HealthCheckIntegration(config_dir=tmp_path)
        integration.config.enabled = False

        # Test notify backup success when disabled
        results = integration.notify_backup_success("backup_001")

        # Should return empty dict when disabled
        assert results == {}

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_uptime_kuma_push_integration(self, mock_post, tmp_path):
        """Test Uptime Kuma push monitor integration"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        service_config = HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.CUSTOM_HTTP,
            ping_url="https://uptime.example.com/api/push/abc123"
        )

        # Create integration with temp config dir
        integration = HealthCheckIntegration(config_dir=tmp_path)
        
        # Add service configuration
        integration.add_service("uptime_kuma", service_config)
        integration.config.enabled = True
        integration.config.ping_on_backup_success = True

        # Test notify backup success
        results = integration.notify_backup_success("backup_001")

        assert "uptime_kuma" in results
        assert results["uptime_kuma"].success is True
        mock_post.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_multiple_health_check_services(self, mock_post, health_check_service_config, tmp_path):
        """Test integration with multiple health check services"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Create integration with temp config dir
        integration = HealthCheckIntegration(config_dir=tmp_path)
        
        # Add multiple service configurations
        integration.add_service("healthchecks_io", health_check_service_config)
        integration.add_service("uptime_kuma", HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.CUSTOM_HTTP,
            ping_url="https://uptime.example.com/api/push/abc123"
        ))
        integration.config.enabled = True
        integration.config.ping_on_backup_success = True

        # Test notify backup success
        results = integration.notify_backup_success("backup_001")

        assert len(results) == 2
        assert "healthchecks_io" in results
        assert "uptime_kuma" in results
        assert results["healthchecks_io"].success is True
        assert results["uptime_kuma"].success is True
        # Both services should be called
        assert mock_post.call_count == 2
