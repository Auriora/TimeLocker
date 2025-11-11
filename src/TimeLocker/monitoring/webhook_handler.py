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

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import requests

from .status_reporter import OperationStatus

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Base exception for webhook-related errors"""
    pass


class PayloadFormat(Enum):
    """Supported webhook payload formats"""
    JSON = "json"
    FORM = "form"
    CUSTOM = "custom"


@dataclass
class WebhookConfig:
    """Configuration for webhook integration"""
    enabled: bool = False
    url: str = ""
    payload_format: PayloadFormat = PayloadFormat.JSON
    custom_headers: Dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True
    timeout: int = 10  # seconds
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    retry_backoff_multiplier: float = 2.0
    include_metadata: bool = True
    include_progress: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.enabled and not self.url:
            raise ValueError("Webhook URL is required when webhooks are enabled")
        
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")


@dataclass
class WebhookResult:
    """Result of a webhook delivery attempt"""
    success: bool
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int = 1
    total_duration: float = 0.0  # seconds
    timestamp: datetime = field(default_factory=datetime.now)


class RetryHandler:
    """Handles retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0, 
                 backoff_multiplier: float = 2.0):
        """
        Initialize retry handler
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_multiplier = backoff_multiplier
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt using exponential backoff
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            float: Delay in seconds
        """
        return self.initial_delay * (self.backoff_multiplier ** attempt)
    
    def should_retry(self, attempt: int, status_code: Optional[int] = None) -> bool:
        """
        Determine if a retry should be attempted
        
        Args:
            attempt: Current attempt number (0-indexed)
            status_code: HTTP status code from previous attempt
            
        Returns:
            bool: True if retry should be attempted
        """
        if attempt >= self.max_retries:
            return False
        
        # Retry on network errors (status_code is None) or server errors (5xx)
        if status_code is None:
            return True
        
        if 500 <= status_code < 600:
            return True
        
        # Don't retry on client errors (4xx) except 429 (rate limit)
        if status_code == 429:
            return True
        
        return False


class WebhookHandler:
    """
    Handles webhook notifications for backup events.
    
    Features:
    - Configurable webhook URLs and payload formats
    - Retry logic with exponential backoff
    - SSL certificate validation options
    - Custom headers support
    - Webhook testing and validation
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize webhook handler
        
        Args:
            config_dir: Directory for webhook configuration
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "webhooks"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / "webhook_config.json"
        self.config = self._load_config()
        
        self.retry_handler = RetryHandler(
            max_retries=self.config.max_retries,
            initial_delay=self.config.retry_delay,
            backoff_multiplier=self.config.retry_backoff_multiplier
        )
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.config.custom_headers)
    
    def _load_config(self) -> WebhookConfig:
        """Load webhook configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    # Convert payload_format string to enum
                    if 'payload_format' in data and isinstance(data['payload_format'], str):
                        data['payload_format'] = PayloadFormat(data['payload_format'])
                    return WebhookConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load webhook config: {e}")
        
        return WebhookConfig()
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            config_dict = {
                'enabled': self.config.enabled,
                'url': self.config.url,
                'payload_format': self.config.payload_format.value,
                'custom_headers': self.config.custom_headers,
                'verify_ssl': self.config.verify_ssl,
                'timeout': self.config.timeout,
                'max_retries': self.config.max_retries,
                'retry_delay': self.config.retry_delay,
                'retry_backoff_multiplier': self.config.retry_backoff_multiplier,
                'include_metadata': self.config.include_metadata,
                'include_progress': self.config.include_progress
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save webhook config: {e}")
            raise WebhookError(f"Failed to save webhook config: {e}")
    
    def update_config(self, **kwargs) -> None:
        """
        Update webhook configuration
        
        Args:
            **kwargs: Configuration key-value pairs to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Update retry handler if retry settings changed
        if any(k in kwargs for k in ['max_retries', 'retry_delay', 'retry_backoff_multiplier']):
            self.retry_handler = RetryHandler(
                max_retries=self.config.max_retries,
                initial_delay=self.config.retry_delay,
                backoff_multiplier=self.config.retry_backoff_multiplier
            )
        
        # Update session headers if custom_headers changed
        if 'custom_headers' in kwargs:
            self.session.headers.update(self.config.custom_headers)
        
        self.save_config()
    
    def validate_webhook_config(self, config: Optional[WebhookConfig] = None) -> Dict[str, Any]:
        """
        Validate webhook configuration
        
        Args:
            config: Configuration to validate (uses current config if None)
            
        Returns:
            Dict with validation results
        """
        if config is None:
            config = self.config
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate URL
        if not config.url:
            validation_result['valid'] = False
            validation_result['errors'].append("Webhook URL is required")
        else:
            try:
                parsed = urlparse(config.url)
                if not parsed.scheme:
                    validation_result['valid'] = False
                    validation_result['errors'].append("URL must include scheme (http:// or https://)")
                elif parsed.scheme not in ['http', 'https']:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Unsupported URL scheme: {parsed.scheme}")
                
                if not parsed.netloc:
                    validation_result['valid'] = False
                    validation_result['errors'].append("URL must include hostname")
                
                # Warn about non-SSL URLs
                if parsed.scheme == 'http':
                    validation_result['warnings'].append("Using non-SSL URL (http://). Consider using https:// for security")
            except Exception as e:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Invalid URL format: {e}")
        
        # Validate timeout
        if config.timeout <= 0:
            validation_result['valid'] = False
            validation_result['errors'].append("Timeout must be positive")
        elif config.timeout < 5:
            validation_result['warnings'].append("Timeout is very short (< 5 seconds)")
        
        # Validate retry settings
        if config.max_retries < 0:
            validation_result['valid'] = False
            validation_result['errors'].append("max_retries must be non-negative")
        elif config.max_retries > 10:
            validation_result['warnings'].append("max_retries is very high (> 10)")
        
        if config.retry_delay < 0:
            validation_result['valid'] = False
            validation_result['errors'].append("retry_delay must be non-negative")
        
        # Warn about SSL verification disabled
        if not config.verify_ssl:
            validation_result['warnings'].append("SSL certificate verification is disabled. This is insecure.")
        
        return validation_result
    
    def _build_payload(self, status: OperationStatus) -> Dict[str, Any]:
        """
        Build webhook payload from operation status
        
        Args:
            status: Operation status to convert to payload
            
        Returns:
            Dict containing payload data
        """
        payload = {
            'event_type': status.operation_type,
            'status': status.status.value,
            'message': status.message,
            'timestamp': status.timestamp.isoformat(),
            'operation_id': status.operation_id
        }
        
        # Add optional fields
        if status.repository_id:
            payload['repository_id'] = status.repository_id
        
        if self.config.include_progress:
            if status.progress_percentage is not None:
                payload['progress_percentage'] = status.progress_percentage
            if status.files_processed is not None:
                payload['files_processed'] = status.files_processed
            if status.total_files is not None:
                payload['total_files'] = status.total_files
            if status.bytes_processed is not None:
                payload['bytes_processed'] = status.bytes_processed
        
        if self.config.include_metadata and status.metadata:
            payload['metadata'] = status.metadata
        
        return payload
    
    def send_webhook(self, status: OperationStatus) -> WebhookResult:
        """
        Send webhook notification for backup event
        
        Args:
            status: Operation status to send
            
        Returns:
            WebhookResult with delivery status
        """
        if not self.config.enabled:
            return WebhookResult(
                success=False,
                error_message="Webhooks are disabled",
                attempts=0
            )
        
        payload = self._build_payload(status)
        start_time = time.time()
        
        attempt = 0
        last_error = None
        last_status_code = None
        
        while attempt <= self.config.max_retries:
            try:
                # Prepare request based on payload format
                if self.config.payload_format == PayloadFormat.JSON:
                    response = self.session.post(
                        self.config.url,
                        json=payload,
                        timeout=self.config.timeout,
                        verify=self.config.verify_ssl
                    )
                elif self.config.payload_format == PayloadFormat.FORM:
                    response = self.session.post(
                        self.config.url,
                        data=payload,
                        timeout=self.config.timeout,
                        verify=self.config.verify_ssl
                    )
                else:
                    # Custom format - send as JSON by default
                    response = self.session.post(
                        self.config.url,
                        json=payload,
                        timeout=self.config.timeout,
                        verify=self.config.verify_ssl
                    )
                
                last_status_code = response.status_code
                
                # Check if request was successful
                if response.ok:
                    total_duration = time.time() - start_time
                    logger.info(f"Webhook delivered successfully after {attempt + 1} attempt(s)")
                    return WebhookResult(
                        success=True,
                        status_code=response.status_code,
                        response_body=response.text[:500],  # Limit response body size
                        attempts=attempt + 1,
                        total_duration=total_duration
                    )
                
                # Request failed, check if we should retry
                if not self.retry_handler.should_retry(attempt, response.status_code):
                    total_duration = time.time() - start_time
                    error_msg = f"Webhook failed with status {response.status_code}: {response.text[:200]}"
                    logger.error(error_msg)
                    return WebhookResult(
                        success=False,
                        status_code=response.status_code,
                        response_body=response.text[:500],
                        error_message=error_msg,
                        attempts=attempt + 1,
                        total_duration=total_duration
                    )
                
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                
            except requests.exceptions.Timeout as e:
                last_error = f"Request timeout: {e}"
                logger.warning(f"Webhook attempt {attempt + 1} timed out: {e}")
            except requests.exceptions.SSLError as e:
                last_error = f"SSL error: {e}"
                logger.error(f"Webhook SSL error: {e}")
                # Don't retry SSL errors
                break
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                logger.warning(f"Webhook attempt {attempt + 1} connection failed: {e}")
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.error(f"Webhook attempt {attempt + 1} failed: {e}")
            
            # Check if we should retry
            if not self.retry_handler.should_retry(attempt, last_status_code):
                break
            
            # Wait before retrying
            if attempt < self.config.max_retries:
                delay = self.retry_handler.calculate_delay(attempt)
                logger.info(f"Retrying webhook in {delay:.1f} seconds...")
                time.sleep(delay)
            
            attempt += 1
        
        # All attempts failed
        total_duration = time.time() - start_time
        error_msg = f"Webhook failed after {attempt + 1} attempt(s): {last_error}"
        logger.error(error_msg)
        
        return WebhookResult(
            success=False,
            status_code=last_status_code,
            error_message=error_msg,
            attempts=attempt + 1,
            total_duration=total_duration
        )
    
    def test_webhook(self) -> WebhookResult:
        """
        Test webhook configuration by sending a test payload
        
        Returns:
            WebhookResult with test status
        """
        from .status_reporter import StatusLevel
        
        test_status = OperationStatus(
            operation_id="webhook_test",
            operation_type="test",
            status=StatusLevel.SUCCESS,
            message="This is a test webhook from TimeLocker",
            timestamp=datetime.now()
        )
        
        logger.info("Sending test webhook...")
        result = self.send_webhook(test_status)
        
        if result.success:
            logger.info(f"Test webhook successful (status: {result.status_code})")
        else:
            logger.error(f"Test webhook failed: {result.error_message}")
        
        return result
    
    def shutdown(self) -> None:
        """Clean up resources"""
        try:
            self.session.close()
        except Exception as e:
            logger.warning(f"Error closing webhook session: {e}")
