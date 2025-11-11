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


class TestWebhookIntegration:
    """Integration tests for webhook functionality"""

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_webhook_config_creation(self):
        """Test creating webhook configuration"""
        config = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            events=["backup_completed", "backup_failed"],
            payload_format=PayloadFormat.JSON,
            headers={"Authorization": "Bearer token123"}
        )

        assert config.url == "https://example.com/webhook"
        assert config.enabled is True
        assert "backup_completed" in config.events

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.post')
    def test_webhook_send_success(self, mock_post):
        """Test successful webhook delivery"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        config = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            events=["backup_completed"]
        )

        handler = WebhookHandler(config)

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Backup completed",
            timestamp=datetime.now()
        )

        result = handler.send_webhook("backup_completed", status.to_dict())

        assert result.success is True
        assert result.status_code == 200
        mock_post.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.post')
    def test_webhook_send_failure(self, mock_post):
        """Test webhook delivery failure"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        config = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            events=["backup_failed"]
        )

        handler = WebhookHandler(config)

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.ERROR,
            message="Backup failed",
            timestamp=datetime.now()
        )

        result = handler.send_webhook("backup_failed", status.to_dict())

        assert result.success is False
        assert result.error_message is not None

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.post')
    def test_webhook_retry_logic(self, mock_post):
        """Test webhook retry logic on failure"""
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            mock_response
        ]

        config = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            events=["backup_completed"],
            retry_count=2,
            retry_delay=0.1
        )

        handler = WebhookHandler(config)

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Backup completed",
            timestamp=datetime.now()
        )

        result = handler.send_webhook("backup_completed", status.to_dict())

        assert result.success is True
        assert mock_post.call_count == 2

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_webhook_event_filtering(self):
        """Test webhook event filtering"""
        config = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            events=["backup_completed"]  # Only this event
        )

        handler = WebhookHandler(config)

        # Should send for backup_completed
        assert handler.should_send_webhook("backup_completed") is True

        # Should not send for backup_failed
        assert handler.should_send_webhook("backup_failed") is False

    @pytest.mark.monitoring
    @pytest.mark.integration
    @patch('requests.post')
    def test_webhook_custom_headers(self, mock_post):
        """Test webhook with custom headers"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        config = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            events=["backup_completed"],
            headers={
                "Authorization": "Bearer secret_token",
                "X-Custom-Header": "custom_value"
            }
        )

        handler = WebhookHandler(config)

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Backup completed",
            timestamp=datetime.now()
        )

        handler.send_webhook("backup_completed", status.to_dict())

        # Verify headers were included
        call_kwargs = mock_post.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert "X-Custom-Header" in call_kwargs["headers"]
