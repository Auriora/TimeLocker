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
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any
from urllib.parse import urljoin, urlparse
import requests

logger = logging.getLogger(__name__)


class HealthCheckError(Exception):
    """Base exception for health check-related errors"""
    pass


class HealthCheckServiceType(Enum):
    """Supported health check service types"""
    HEALTHCHECKS_IO = "healthchecks.io"
    CUSTOM_HTTP = "custom_http"


class HealthStatus(Enum):
    """Health status values"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckServiceConfig:
    """Configuration for a specific health check service"""
    service_type: HealthCheckServiceType
    enabled: bool = True
    ping_url: str = ""
    api_key: Optional[str] = None
    check_uuid: Optional[str] = None  # For healthchecks.io
    timeout: int = 10  # seconds
    custom_headers: Dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.enabled and not self.ping_url:
            raise ValueError("ping_url is required when health check is enabled")


@dataclass
class HealthCheckConfig:
    """Configuration for health check integration"""
    enabled: bool = False
    ping_interval: int = 60  # seconds
    ping_on_backup_start: bool = True
    ping_on_backup_success: bool = True
    ping_on_backup_failure: bool = True
    include_logs: bool = False
    max_log_size: int = 10000  # characters
    services: Dict[str, HealthCheckServiceConfig] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.ping_interval <= 0:
            raise ValueError("ping_interval must be positive")


@dataclass
class PingResult:
    """Result of a health check ping"""
    success: bool
    service_name: str
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0  # seconds


class HealthCheckIntegration:
    """
    Integration with external health check services.
    
    Supports:
    - healthchecks.io ping endpoints
    - Custom HTTP health check endpoints
    - Configurable ping intervals and timeouts
    - Automatic periodic pinging
    - Event-based pinging (backup start/success/failure)
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize health check integration
        
        Args:
            config_dir: Directory for health check configuration
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "health_checks"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / "health_check_config.json"
        self.config = self._load_config()
        
        # Session for connection pooling
        self.session = requests.Session()
        
        # Periodic ping thread
        self._ping_thread: Optional[threading.Thread] = None
        self._stop_ping_thread = threading.Event()
        self._last_ping_time: Optional[datetime] = None
        
        # Start periodic pinging if enabled
        if self.config.enabled and self.config.ping_interval > 0:
            self.start_periodic_ping()
    
    def _load_config(self) -> HealthCheckConfig:
        """Load health check configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                    # Convert services dict
                    if 'services' in data:
                        services = {}
                        for name, service_data in data['services'].items():
                            if 'service_type' in service_data and isinstance(service_data['service_type'], str):
                                service_data['service_type'] = HealthCheckServiceType(service_data['service_type'])
                            services[name] = HealthCheckServiceConfig(**service_data)
                        data['services'] = services
                    
                    return HealthCheckConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load health check config: {e}")
        
        return HealthCheckConfig()
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            config_dict = {
                'enabled': self.config.enabled,
                'ping_interval': self.config.ping_interval,
                'ping_on_backup_start': self.config.ping_on_backup_start,
                'ping_on_backup_success': self.config.ping_on_backup_success,
                'ping_on_backup_failure': self.config.ping_on_backup_failure,
                'include_logs': self.config.include_logs,
                'max_log_size': self.config.max_log_size,
                'services': {}
            }
            
            # Convert services
            for name, service in self.config.services.items():
                config_dict['services'][name] = {
                    'service_type': service.service_type.value,
                    'enabled': service.enabled,
                    'ping_url': service.ping_url,
                    'api_key': service.api_key,
                    'check_uuid': service.check_uuid,
                    'timeout': service.timeout,
                    'custom_headers': service.custom_headers,
                    'verify_ssl': service.verify_ssl
                }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save health check config: {e}")
            raise HealthCheckError(f"Failed to save health check config: {e}")
    
    def add_service(self, name: str, service_config: HealthCheckServiceConfig) -> None:
        """
        Add a health check service
        
        Args:
            name: Service name
            service_config: Service configuration
        """
        self.config.services[name] = service_config
        self.save_config()
    
    def remove_service(self, name: str) -> None:
        """
        Remove a health check service
        
        Args:
            name: Service name to remove
        """
        if name in self.config.services:
            del self.config.services[name]
            self.save_config()
    
    def configure_healthchecks_io(self, name: str, check_uuid: str, 
                                   api_key: Optional[str] = None) -> None:
        """
        Configure healthchecks.io integration
        
        Args:
            name: Service name
            check_uuid: Check UUID from healthchecks.io
            api_key: Optional API key for authenticated requests
        """
        ping_url = f"https://hc-ping.com/{check_uuid}"
        
        service_config = HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.HEALTHCHECKS_IO,
            enabled=True,
            ping_url=ping_url,
            api_key=api_key,
            check_uuid=check_uuid,
            timeout=10,
            verify_ssl=True
        )
        
        self.add_service(name, service_config)
        logger.info(f"Configured healthchecks.io service: {name}")
    
    def configure_custom_http(self, name: str, ping_url: str, 
                             custom_headers: Optional[Dict[str, str]] = None,
                             verify_ssl: bool = True) -> None:
        """
        Configure custom HTTP health check endpoint
        
        Args:
            name: Service name
            ping_url: URL to ping
            custom_headers: Optional custom headers
            verify_ssl: Whether to verify SSL certificates
        """
        service_config = HealthCheckServiceConfig(
            service_type=HealthCheckServiceType.CUSTOM_HTTP,
            enabled=True,
            ping_url=ping_url,
            timeout=10,
            custom_headers=custom_headers or {},
            verify_ssl=verify_ssl
        )
        
        self.add_service(name, service_config)
        logger.info(f"Configured custom HTTP health check service: {name}")
    
    def validate_service_config(self, service_config: HealthCheckServiceConfig) -> Dict[str, Any]:
        """
        Validate health check service configuration
        
        Args:
            service_config: Service configuration to validate
            
        Returns:
            Dict with validation results
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate ping URL
        if not service_config.ping_url:
            validation_result['valid'] = False
            validation_result['errors'].append("ping_url is required")
        else:
            try:
                parsed = urlparse(service_config.ping_url)
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
                    validation_result['warnings'].append("Using non-SSL URL. Consider using https:// for security")
            except Exception as e:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Invalid URL format: {e}")
        
        # Validate timeout
        if service_config.timeout <= 0:
            validation_result['valid'] = False
            validation_result['errors'].append("timeout must be positive")
        
        # Warn about SSL verification disabled
        if not service_config.verify_ssl:
            validation_result['warnings'].append("SSL certificate verification is disabled. This is insecure.")
        
        # Validate healthchecks.io specific config
        if service_config.service_type == HealthCheckServiceType.HEALTHCHECKS_IO:
            if not service_config.check_uuid:
                validation_result['warnings'].append("check_uuid not set for healthchecks.io service")
        
        return validation_result
    
    def ping_health_check(self, status: HealthStatus, 
                         message: Optional[str] = None,
                         logs: Optional[str] = None) -> Dict[str, PingResult]:
        """
        Send health check ping with current status
        
        Args:
            status: Current health status
            message: Optional status message
            logs: Optional log data to include
            
        Returns:
            Dict mapping service names to ping results
        """
        if not self.config.enabled:
            logger.debug("Health check integration is disabled")
            return {}
        
        results = {}
        
        for service_name, service_config in self.config.services.items():
            if not service_config.enabled:
                continue
            
            try:
                result = self._ping_service(service_config, status, message, logs)
                results[service_name] = result
                
                if result.success:
                    logger.info(f"Health check ping successful for {service_name}")
                else:
                    logger.warning(f"Health check ping failed for {service_name}: {result.error_message}")
            except Exception as e:
                logger.error(f"Failed to ping health check service {service_name}: {e}")
                results[service_name] = PingResult(
                    success=False,
                    service_name=service_name,
                    error_message=str(e)
                )
        
        self._last_ping_time = datetime.now()
        return results
    
    def _ping_service(self, service_config: HealthCheckServiceConfig,
                     status: HealthStatus, message: Optional[str] = None,
                     logs: Optional[str] = None) -> PingResult:
        """
        Ping a specific health check service
        
        Args:
            service_config: Service configuration
            status: Health status
            message: Optional message
            logs: Optional logs
            
        Returns:
            PingResult with ping status
        """
        start_time = time.time()
        
        try:
            # Build URL based on service type and status
            url = service_config.ping_url
            
            if service_config.service_type == HealthCheckServiceType.HEALTHCHECKS_IO:
                # healthchecks.io supports /start, /fail, and success (no suffix)
                if status == HealthStatus.UNHEALTHY:
                    url = urljoin(url + '/', 'fail')
                # For healthy/degraded, use the base URL (success)
            
            # Prepare headers
            headers = dict(service_config.custom_headers)
            if service_config.api_key:
                headers['Authorization'] = f"Bearer {service_config.api_key}"
            
            # Prepare data
            data = None
            if message or logs:
                payload = {}
                if message:
                    payload['message'] = message
                if logs and self.config.include_logs:
                    # Truncate logs if needed
                    truncated_logs = logs[:self.config.max_log_size]
                    payload['logs'] = truncated_logs
                data = json.dumps(payload)
                headers['Content-Type'] = 'application/json'
            
            # Send ping
            response = self.session.post(
                url,
                data=data,
                headers=headers,
                timeout=service_config.timeout,
                verify=service_config.verify_ssl
            )
            
            duration = time.time() - start_time
            
            if response.ok:
                return PingResult(
                    success=True,
                    service_name="",  # Will be set by caller
                    status_code=response.status_code,
                    response_body=response.text[:200],
                    duration=duration
                )
            else:
                return PingResult(
                    success=False,
                    service_name="",
                    status_code=response.status_code,
                    response_body=response.text[:200],
                    error_message=f"HTTP {response.status_code}: {response.text[:100]}",
                    duration=duration
                )
        
        except requests.exceptions.Timeout as e:
            duration = time.time() - start_time
            return PingResult(
                success=False,
                service_name="",
                error_message=f"Request timeout: {e}",
                duration=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            return PingResult(
                success=False,
                service_name="",
                error_message=f"Ping failed: {e}",
                duration=duration
            )
    
    def start_periodic_ping(self) -> None:
        """Start periodic health check pinging in background thread"""
        if self._ping_thread and self._ping_thread.is_alive():
            logger.warning("Periodic ping thread already running")
            return
        
        self._stop_ping_thread.clear()
        self._ping_thread = threading.Thread(target=self._periodic_ping_loop, daemon=True)
        self._ping_thread.start()
        logger.info(f"Started periodic health check pinging (interval: {self.config.ping_interval}s)")
    
    def stop_periodic_ping(self) -> None:
        """Stop periodic health check pinging"""
        if not self._ping_thread or not self._ping_thread.is_alive():
            return
        
        self._stop_ping_thread.set()
        self._ping_thread.join(timeout=5)
        logger.info("Stopped periodic health check pinging")
    
    def _periodic_ping_loop(self) -> None:
        """Background thread loop for periodic pinging"""
        while not self._stop_ping_thread.is_set():
            try:
                # Send periodic ping with healthy status
                self.ping_health_check(HealthStatus.HEALTHY, message="Periodic health check")
            except Exception as e:
                logger.error(f"Error in periodic ping: {e}")
            
            # Wait for next interval or stop signal
            self._stop_ping_thread.wait(timeout=self.config.ping_interval)
    
    def notify_backup_start(self, repository_id: str) -> Dict[str, PingResult]:
        """
        Notify health check services of backup start
        
        Args:
            repository_id: Repository being backed up
            
        Returns:
            Dict of ping results
        """
        if not self.config.ping_on_backup_start:
            return {}
        
        message = f"Backup started for repository: {repository_id}"
        return self.ping_health_check(HealthStatus.HEALTHY, message=message)
    
    def notify_backup_success(self, repository_id: str, 
                             duration: Optional[timedelta] = None) -> Dict[str, PingResult]:
        """
        Notify health check services of backup success
        
        Args:
            repository_id: Repository that was backed up
            duration: Backup duration
            
        Returns:
            Dict of ping results
        """
        if not self.config.ping_on_backup_success:
            return {}
        
        message = f"Backup completed successfully for repository: {repository_id}"
        if duration:
            message += f" (duration: {duration})"
        
        return self.ping_health_check(HealthStatus.HEALTHY, message=message)
    
    def notify_backup_failure(self, repository_id: str, 
                             error: str) -> Dict[str, PingResult]:
        """
        Notify health check services of backup failure
        
        Args:
            repository_id: Repository that failed
            error: Error message
            
        Returns:
            Dict of ping results
        """
        if not self.config.ping_on_backup_failure:
            return {}
        
        message = f"Backup failed for repository: {repository_id}. Error: {error}"
        return self.ping_health_check(HealthStatus.UNHEALTHY, message=message)
    
    def test_service(self, service_name: str) -> PingResult:
        """
        Test a specific health check service
        
        Args:
            service_name: Name of service to test
            
        Returns:
            PingResult with test status
        """
        if service_name not in self.config.services:
            return PingResult(
                success=False,
                service_name=service_name,
                error_message=f"Service '{service_name}' not found"
            )
        
        service_config = self.config.services[service_name]
        
        logger.info(f"Testing health check service: {service_name}")
        result = self._ping_service(
            service_config,
            HealthStatus.HEALTHY,
            message="Test ping from TimeLocker"
        )
        result.service_name = service_name
        
        if result.success:
            logger.info(f"Test successful for {service_name}")
        else:
            logger.error(f"Test failed for {service_name}: {result.error_message}")
        
        return result
    
    def get_last_ping_time(self) -> Optional[datetime]:
        """
        Get timestamp of last successful ping
        
        Returns:
            Datetime of last ping, or None if never pinged
        """
        return self._last_ping_time
    
    def shutdown(self) -> None:
        """Clean up resources"""
        try:
            self.stop_periodic_ping()
            self.session.close()
        except Exception as e:
            logger.warning(f"Error during health check integration shutdown: {e}")
