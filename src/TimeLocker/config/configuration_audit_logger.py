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
import os
import socket
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigurationAuditLevel(Enum):
    """Audit levels for configuration operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfigurationOperation(Enum):
    """Types of configuration operations"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    CREATE = "create"
    UPDATE = "update"
    BACKUP = "backup"
    RESTORE = "restore"
    MIGRATE = "migrate"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    SIGN = "sign"
    VERIFY = "verify"
    LOCK = "lock"
    UNLOCK = "unlock"


@dataclass
class ConfigurationAuditEvent:
    """Represents a configuration audit event"""
    timestamp: datetime
    operation: ConfigurationOperation
    level: ConfigurationAuditLevel
    section: Optional[str]
    key: Optional[str]
    user_id: Optional[str]
    process_id: int
    hostname: str
    success: bool
    description: str
    old_value_hash: Optional[str] = None
    new_value_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class ConfigurationAccessPattern:
    """Represents access patterns for monitoring"""
    user_id: str
    operation_counts: Dict[str, int]
    last_access: datetime
    suspicious_activity_score: float
    failed_attempts: int
    access_locations: Set[str]


class ConfigurationAuditLogger:
    """
    Comprehensive audit logging for configuration operations.
    
    Provides detailed audit trails for all configuration access and modifications,
    integrating with security services for enhanced monitoring and alerting.
    """

    def __init__(self, config_dir: Optional[Path] = None, 
                 security_service: Optional['SecurityService'] = None):
        """
        Initialize configuration audit logger.
        
        Args:
            config_dir: Configuration directory for audit logs
            security_service: SecurityService instance for enhanced logging
        """
        if config_dir is None:
            from .configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory()
        
        self.config_dir = Path(config_dir)
        self.audit_dir = self.config_dir / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        self.security_service = security_service
        
        # Audit log files
        self.audit_log_file = self.audit_dir / "configuration_audit.log"
        self.access_patterns_file = self.audit_dir / "access_patterns.json"
        self.security_alerts_file = self.audit_dir / "security_alerts.log"
        
        # Thread safety
        self._audit_lock = threading.RLock()
        
        # Access pattern tracking
        self._access_patterns: Dict[str, ConfigurationAccessPattern] = {}
        self._load_access_patterns()
        
        # Security thresholds
        self.max_failed_attempts = 5
        self.suspicious_activity_threshold = 50.0
        self.access_rate_limit = 100  # operations per hour
        
        # Initialize audit log
        self._initialize_audit_log()

    def _initialize_audit_log(self) -> None:
        """Initialize audit log with proper headers"""
        if not self.audit_log_file.exists():
            with open(self.audit_log_file, 'w') as f:
                f.write("# TimeLocker Configuration Audit Log\n")
                f.write(f"# Initialized: {datetime.now().isoformat()}\n")
                f.write("# Format: JSON lines with audit event data\n")

    def log_configuration_access(
        self,
        operation: ConfigurationOperation,
        section: Optional[str] = None,
        key: Optional[str] = None,
        success: bool = True,
        description: str = "",
        old_value: Any = None,
        new_value: Any = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log configuration access event.
        
        Args:
            operation: Type of configuration operation
            section: Configuration section accessed
            key: Configuration key accessed
            success: Whether operation was successful
            description: Human-readable description
            old_value: Previous value (for updates)
            new_value: New value (for updates)
            user_id: User performing the operation
            metadata: Additional metadata
        """
        try:
            with self._audit_lock:
                # Determine audit level
                level = self._determine_audit_level(operation, success)
                
                # Get user context
                if user_id is None:
                    user_id = self._get_current_user()
                
                # Create audit event
                audit_event = ConfigurationAuditEvent(
                    timestamp=datetime.now(),
                    operation=operation,
                    level=level,
                    section=section,
                    key=key,
                    user_id=user_id,
                    process_id=os.getpid(),
                    hostname=socket.gethostname(),
                    success=success,
                    description=description,
                    old_value_hash=self._hash_value(old_value) if old_value is not None else None,
                    new_value_hash=self._hash_value(new_value) if new_value is not None else None,
                    metadata=metadata or {},
                    session_id=self._get_session_id()
                )
                
                # Write to audit log
                self._write_audit_event(audit_event)
                
                # Update access patterns
                self._update_access_patterns(audit_event)
                
                # Check for suspicious activity
                self._check_suspicious_activity(audit_event)
                
                # Log to security service if available
                if self.security_service:
                    self._log_to_security_service(audit_event)
                
        except Exception as e:
            logger.error(f"Failed to log configuration access: {e}")

    def _determine_audit_level(
        self,
        operation: ConfigurationOperation,
        success: bool
    ) -> ConfigurationAuditLevel:
        """
        Determine appropriate audit level for operation.
        
        Args:
            operation: Configuration operation
            success: Whether operation was successful
            
        Returns:
            ConfigurationAuditLevel: Appropriate audit level
        """
        if not success:
            return ConfigurationAuditLevel.HIGH
        
        high_risk_operations = {
            ConfigurationOperation.DELETE,
            ConfigurationOperation.MIGRATE,
            ConfigurationOperation.RESTORE
        }
        
        medium_risk_operations = {
            ConfigurationOperation.WRITE,
            ConfigurationOperation.UPDATE,
            ConfigurationOperation.ENCRYPT,
            ConfigurationOperation.DECRYPT
        }
        
        if operation in high_risk_operations:
            return ConfigurationAuditLevel.HIGH
        elif operation in medium_risk_operations:
            return ConfigurationAuditLevel.MEDIUM
        else:
            return ConfigurationAuditLevel.LOW

    def _get_current_user(self) -> str:
        """Get current user identifier"""
        try:
            return os.getenv('USER', os.getenv('USERNAME', 'unknown'))
        except Exception:
            return 'unknown'

    def _get_session_id(self) -> str:
        """Get current session identifier"""
        # Simple session ID based on process ID and start time
        return f"pid_{os.getpid()}_{int(datetime.now().timestamp())}"

    def _hash_value(self, value: Any) -> str:
        """Create hash of configuration value for audit trail"""
        import hashlib
        try:
            if value is None:
                return "null"
            value_str = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
            return hashlib.sha256(value_str.encode('utf-8')).hexdigest()[:16]
        except Exception:
            return "unhashable"

    def _write_audit_event(self, event: ConfigurationAuditEvent) -> None:
        """Write audit event to log file"""
        try:
            event_dict = asdict(event)
            # Convert datetime and enum objects to strings
            event_dict['timestamp'] = event.timestamp.isoformat()
            event_dict['operation'] = event.operation.value
            event_dict['level'] = event.level.value
            
            with open(self.audit_log_file, 'a') as f:
                f.write(json.dumps(event_dict) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")

    def _update_access_patterns(self, event: ConfigurationAuditEvent) -> None:
        """Update access patterns for user behavior analysis"""
        try:
            user_id = event.user_id or 'unknown'
            
            if user_id not in self._access_patterns:
                self._access_patterns[user_id] = ConfigurationAccessPattern(
                    user_id=user_id,
                    operation_counts={},
                    last_access=event.timestamp,
                    suspicious_activity_score=0.0,
                    failed_attempts=0,
                    access_locations={event.hostname}
                )
            
            pattern = self._access_patterns[user_id]
            
            # Update operation counts
            op_name = event.operation.value
            pattern.operation_counts[op_name] = pattern.operation_counts.get(op_name, 0) + 1
            pattern.last_access = event.timestamp
            pattern.access_locations.add(event.hostname)
            
            # Update failed attempts
            if not event.success:
                pattern.failed_attempts += 1
            else:
                pattern.failed_attempts = max(0, pattern.failed_attempts - 1)
            
            # Calculate suspicious activity score
            pattern.suspicious_activity_score = self._calculate_suspicious_score(pattern, event)
            
            # Save updated patterns
            self._save_access_patterns()
            
        except Exception as e:
            logger.error(f"Failed to update access patterns: {e}")

    def _calculate_suspicious_score(
        self,
        pattern: ConfigurationAccessPattern,
        event: ConfigurationAuditEvent
    ) -> float:
        """
        Calculate suspicious activity score for user.
        
        Args:
            pattern: User access pattern
            event: Current audit event
            
        Returns:
            float: Suspicious activity score (0-100)
        """
        score = 0.0
        
        # Failed attempts contribute to suspicion
        score += pattern.failed_attempts * 10
        
        # High frequency of operations
        total_operations = sum(pattern.operation_counts.values())
        time_since_first = (event.timestamp - pattern.last_access).total_seconds() / 3600
        if time_since_first > 0:
            operations_per_hour = total_operations / time_since_first
            if operations_per_hour > self.access_rate_limit:
                score += 20
        
        # Multiple access locations
        if len(pattern.access_locations) > 3:
            score += 15
        
        # High-risk operations
        high_risk_ops = ['delete', 'migrate', 'restore']
        high_risk_count = sum(
            pattern.operation_counts.get(op, 0) for op in high_risk_ops
        )
        score += high_risk_count * 5
        
        # Off-hours access (simple heuristic)
        hour = event.timestamp.hour
        if hour < 6 or hour > 22:  # Outside normal business hours
            score += 10
        
        return min(100.0, score)

    def _check_suspicious_activity(self, event: ConfigurationAuditEvent) -> None:
        """Check for suspicious activity and generate alerts"""
        try:
            user_id = event.user_id or 'unknown'
            pattern = self._access_patterns.get(user_id)
            
            if not pattern:
                return
            
            alerts = []
            
            # Check failed attempts threshold
            if pattern.failed_attempts >= self.max_failed_attempts:
                alerts.append({
                    "type": "excessive_failed_attempts",
                    "severity": "high",
                    "message": f"User {user_id} has {pattern.failed_attempts} failed attempts",
                    "user_id": user_id,
                    "timestamp": event.timestamp.isoformat()
                })
            
            # Check suspicious activity score
            if pattern.suspicious_activity_score >= self.suspicious_activity_threshold:
                alerts.append({
                    "type": "suspicious_activity_pattern",
                    "severity": "medium",
                    "message": f"User {user_id} has suspicious activity score: {pattern.suspicious_activity_score}",
                    "user_id": user_id,
                    "score": pattern.suspicious_activity_score,
                    "timestamp": event.timestamp.isoformat()
                })
            
            # Check multiple locations
            if len(pattern.access_locations) > 5:
                alerts.append({
                    "type": "multiple_access_locations",
                    "severity": "medium",
                    "message": f"User {user_id} accessing from {len(pattern.access_locations)} different locations",
                    "user_id": user_id,
                    "locations": list(pattern.access_locations),
                    "timestamp": event.timestamp.isoformat()
                })
            
            # Write alerts to security alerts log
            for alert in alerts:
                self._write_security_alert(alert)
                
        except Exception as e:
            logger.error(f"Failed to check suspicious activity: {e}")

    def _write_security_alert(self, alert: Dict[str, Any]) -> None:
        """Write security alert to alerts log"""
        try:
            with open(self.security_alerts_file, 'a') as f:
                f.write(json.dumps(alert) + '\n')
                
            # Also log to main logger
            logger.warning(f"Security alert: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Failed to write security alert: {e}")

    def _log_to_security_service(self, event: ConfigurationAuditEvent) -> None:
        """Log audit event to security service"""
        try:
            if not self.security_service:
                return
            
            # Import SecurityLevel from security_service module
            from ..security.security_service import SecurityLevel
            
            # Map audit level to security level
            level_mapping = {
                ConfigurationAuditLevel.LOW: SecurityLevel.LOW,
                ConfigurationAuditLevel.MEDIUM: SecurityLevel.MEDIUM,
                ConfigurationAuditLevel.HIGH: SecurityLevel.HIGH,
                ConfigurationAuditLevel.CRITICAL: SecurityLevel.CRITICAL
            }
            
            # Import SecurityEvent from security_service module
            from ..security.security_service import SecurityEvent
            
            security_event = SecurityEvent(
                timestamp=event.timestamp,
                event_type="configuration_access",
                level=level_mapping.get(event.level, SecurityLevel.MEDIUM),
                description=f"Configuration {event.operation.value}: {event.description}",
                user_id=event.user_id,
                metadata={
                    "operation": event.operation.value,
                    "section": event.section,
                    "key": event.key,
                    "success": event.success,
                    "hostname": event.hostname,
                    "process_id": event.process_id,
                    "session_id": event.session_id
                }
            )
            
            self.security_service.log_security_event(security_event)
            
        except Exception as e:
            logger.error(f"Failed to log to security service: {e}")

    def _load_access_patterns(self) -> None:
        """Load access patterns from disk"""
        try:
            if self.access_patterns_file.exists():
                with open(self.access_patterns_file, 'r') as f:
                    patterns_data = json.load(f)
                
                for user_id, pattern_data in patterns_data.items():
                    self._access_patterns[user_id] = ConfigurationAccessPattern(
                        user_id=user_id,
                        operation_counts=pattern_data.get("operation_counts", {}),
                        last_access=datetime.fromisoformat(pattern_data["last_access"]),
                        suspicious_activity_score=pattern_data.get("suspicious_activity_score", 0.0),
                        failed_attempts=pattern_data.get("failed_attempts", 0),
                        access_locations=set(pattern_data.get("access_locations", []))
                    )
                    
        except Exception as e:
            logger.warning(f"Failed to load access patterns: {e}")

    def _save_access_patterns(self) -> None:
        """Save access patterns to disk"""
        try:
            patterns_data = {}
            for user_id, pattern in self._access_patterns.items():
                patterns_data[user_id] = {
                    "operation_counts": pattern.operation_counts,
                    "last_access": pattern.last_access.isoformat(),
                    "suspicious_activity_score": pattern.suspicious_activity_score,
                    "failed_attempts": pattern.failed_attempts,
                    "access_locations": list(pattern.access_locations)
                }
            
            with open(self.access_patterns_file, 'w') as f:
                json.dump(patterns_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save access patterns: {e}")

    def get_audit_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        operation: Optional[ConfigurationOperation] = None,
        section: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit events with filtering.
        
        Args:
            start_time: Start time for event filtering
            end_time: End time for event filtering
            user_id: Filter by user ID
            operation: Filter by operation type
            section: Filter by configuration section
            limit: Maximum number of events to return
            
        Returns:
            List of audit events matching criteria
        """
        try:
            events = []
            
            if not self.audit_log_file.exists():
                return events
            
            with open(self.audit_log_file, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    
                    try:
                        event_data = json.loads(line.strip())
                        event_time = datetime.fromisoformat(event_data['timestamp'])
                        
                        # Apply filters
                        if start_time and event_time < start_time:
                            continue
                        if end_time and event_time > end_time:
                            continue
                        if user_id and event_data.get('user_id') != user_id:
                            continue
                        if operation and event_data.get('operation') != operation.value:
                            continue
                        if section and event_data.get('section') != section:
                            continue
                        
                        events.append(event_data)
                        
                        if limit and len(events) >= limit:
                            break
                            
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get audit events: {e}")
            return []

    def get_access_patterns(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get access patterns for analysis.
        
        Args:
            user_id: Specific user ID to get patterns for
            
        Returns:
            Dict containing access patterns
        """
        try:
            if user_id:
                pattern = self._access_patterns.get(user_id)
                if pattern:
                    return {
                        user_id: {
                            "operation_counts": pattern.operation_counts,
                            "last_access": pattern.last_access.isoformat(),
                            "suspicious_activity_score": pattern.suspicious_activity_score,
                            "failed_attempts": pattern.failed_attempts,
                            "access_locations": list(pattern.access_locations)
                        }
                    }
                return {}
            else:
                patterns_data = {}
                for uid, pattern in self._access_patterns.items():
                    patterns_data[uid] = {
                        "operation_counts": pattern.operation_counts,
                        "last_access": pattern.last_access.isoformat(),
                        "suspicious_activity_score": pattern.suspicious_activity_score,
                        "failed_attempts": pattern.failed_attempts,
                        "access_locations": list(pattern.access_locations)
                    }
                return patterns_data
                
        except Exception as e:
            logger.error(f"Failed to get access patterns: {e}")
            return {}

    def get_security_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent security alerts.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of security alerts
        """
        try:
            alerts = []
            
            if not self.security_alerts_file.exists():
                return alerts
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with open(self.security_alerts_file, 'r') as f:
                for line in f:
                    try:
                        alert = json.loads(line.strip())
                        alert_time = datetime.fromisoformat(alert['timestamp'])
                        
                        if alert_time >= cutoff_time:
                            alerts.append(alert)
                            
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get security alerts: {e}")
            return []

    def cleanup_old_audit_logs(self, retention_days: int = 90) -> int:
        """
        Clean up old audit logs based on retention policy.
        
        Args:
            retention_days: Number of days to retain logs
            
        Returns:
            int: Number of log entries removed
        """
        try:
            if not self.audit_log_file.exists():
                return 0
            
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            temp_file = self.audit_log_file.with_suffix('.tmp')
            removed_count = 0
            kept_count = 0
            
            with open(self.audit_log_file, 'r') as infile, open(temp_file, 'w') as outfile:
                for line in infile:
                    if line.startswith('#'):
                        outfile.write(line)
                        continue
                    
                    try:
                        event_data = json.loads(line.strip())
                        event_time = datetime.fromisoformat(event_data['timestamp'])
                        
                        if event_time >= cutoff_time:
                            outfile.write(line)
                            kept_count += 1
                        else:
                            removed_count += 1
                            
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # Keep malformed lines
                        outfile.write(line)
                        kept_count += 1
            
            # Replace original file with cleaned version
            temp_file.replace(self.audit_log_file)
            
            logger.info(f"Audit log cleanup: removed {removed_count} entries, kept {kept_count}")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup audit logs: {e}")
            return 0