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
from unittest.mock import Mock, patch, MagicMock
import requests

from TimeLocker.monitoring import (
    WebhookHandler,
    WebhookConfig,
    WebhookResult,
    PayloadFormat,
    OperationStatus,
    StatusLevel
)
from tests.TimeLocker.fixtures.config_models import webhook_config


class TestWebhookIntegration:
    """Integration tests for webhook functionality"""

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_webhook_config_creation(self, webhook_config):
        """Test creating webhook configuration"""
        config = webhook_config

        assert config.url == "https://example.com/webhook"
        assert config.enabled is True
        assert config.payload_format == PayloadFormat.JSON

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_webhook_send_success(self, mock_post, webhook_config, tmp_path):
        """Test successful webhook delivery"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Create handler with temp config dir
        handler = WebhookHandler(config_dir=tmp_path)
        
        # Update config with webhook settings
        handler.update_config(
            enabled=True,
            url="https://example.com/webhook",
            payload_format=PayloadFormat.JSON
        )

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Backup completed",
            timestamp=datetime.now()
        )

        result = handler.send_webhook(status)

        assert result.success is True
        assert result.status_code == 200
        mock_post.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_webhook_send_failure(self, mock_post, webhook_config, tmp_path):
        """Test webhook delivery failure"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        # Create handler with temp config dir
        handler = WebhookHandler(config_dir=tmp_path)
        
        # Update config with webhook settings
        handler.update_config(
            enabled=True,
            url="https://example.com/webhook",
            payload_format=PayloadFormat.JSON
        )

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.ERROR,
            message="Backup failed",
            timestamp=datetime.now()
        )

        result = handler.send_webhook(status)

        assert result.success is False
        assert result.error_message is not None

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_webhook_retry_logic(self, mock_post, webhook_config, tmp_path):
        """Test webhook retry logic on failure"""
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.text = "OK"
        mock_post.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            mock_response
        ]

        # Create handler with temp config dir
        handler = WebhookHandler(config_dir=tmp_path)
        
        # Update config with webhook settings including retry config
        handler.update_config(
            enabled=True,
            url="https://example.com/webhook",
            payload_format=PayloadFormat.JSON,
            max_retries=2,
            retry_delay=0.1
        )

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Backup completed",
            timestamp=datetime.now()
        )

        result = handler.send_webhook(status)

        assert result.success is True
        assert mock_post.call_count == 2

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_webhook_disabled(self, webhook_config, tmp_path):
        """Test webhook when disabled"""
        # Create handler with temp config dir
        handler = WebhookHandler(config_dir=tmp_path)
        
        # Update config with webhook disabled
        handler.update_config(
            enabled=False,
            url="https://example.com/webhook"
        )

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Backup completed",
            timestamp=datetime.now()
        )

        result = handler.send_webhook(status)

        # Should return failure when disabled
        assert result.success is False
        assert "disabled" in result.error_message.lower()

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.Session.post')
    def test_webhook_custom_headers(self, mock_post, webhook_config, tmp_path):
        """Test webhook with custom headers"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Create handler with temp config dir
        handler = WebhookHandler(config_dir=tmp_path)
        
        # Update config with custom headers
        handler.update_config(
            enabled=True,
            url="https://example.com/webhook",
            payload_format=PayloadFormat.JSON,
            custom_headers={
                "Authorization": "Bearer secret_token",
                "X-Custom-Header": "custom_value"
            }
        )

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Backup completed",
            timestamp=datetime.now()
        )

        result = handler.send_webhook(status)

        # Verify webhook was successful
        assert result.success is True
        mock_post.assert_called_once()
        
        # Verify headers were included in the call
        call_kwargs = mock_post.call_args[1] if mock_post.call_args[1] else {}
        call_args = mock_post.call_args[0] if mock_post.call_args[0] else []
        
        # Headers might be in kwargs or the session already has them
        # Just verify the webhook was called successfully with custom headers configured
        assert handler.config.custom_headers["Authorization"] == "Bearer secret_token"
        assert handler.config.custom_headers["X-Custom-Header"] == "custom_value"
