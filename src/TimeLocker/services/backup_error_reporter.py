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

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of backup errors for classification"""
    TRANSIENT = "transient"
    CONFIGURATION = "configuration"
    TOOL_SPECIFIC = "tool_specific"
    RESOURCE = "resource"
    NETWORK = "network"
    PERMISSION = "permission"
    DATA_INTEGRITY = "data_integrity"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for backup errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RemediationStep:
    """Represents a single remediation step for an error"""
    description: str
    command: Optional[str] = None
    documentation_url: Optional[str] = None
    automated: bool = False


@dataclass
class BackupError:
    """Detailed backup error information with remediation guidance"""
    error_id: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    operation_id: str
    repository_id: Optional[str] = None
    tool_name: Optional[str] = None
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    remediation_steps: List[RemediationStep] = field(default_factory=list)
    related_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'error_id': self.error_id,
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'operation_id': self.operation_id,
            'repository_id': self.repository_id,
            'tool_name': self.tool_name,
            'error_code': self.error_code,
            'stack_trace': self.stack_trace,
            'context': self.context,
            'remediation_steps': [
                {
                    'description': step.description,
                    'command': step.command,
                    'documentation_url': step.documentation_url,
                    'automated': step.automated
                }
                for step in self.remediation_steps
            ],
            'related_errors': self.related_errors
        }


@dataclass
class BackupWarning:
    """Represents a non-critical warning during backup operations"""
    warning_id: str
    message: str
    timestamp: datetime
    operation_id: str
    repository_id: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.LOW
    context: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'warning_id': self.warning_id,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'operation_id': self.operation_id,
            'repository_id': self.repository_id,
            'severity': self.severity.value,
            'context': self.context,
            'suggestions': self.suggestions
        }


class BackupErrorReporter:
    """
    Provides detailed error reporting and remediation guidance for backup operations.
    
    This service analyzes backup errors, classifies them, and provides actionable
    remediation steps to help users resolve issues quickly.
    """
    
    def __init__(self):
        """Initialize the backup error reporter"""
        self._error_patterns = self._initialize_error_patterns()
        self._remediation_database = self._initialize_remediation_database()
    
    def classify_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> BackupError:
        """
        Classify an error and generate detailed error report with remediation steps.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            BackupError with classification and remediation guidance
        """
        error_message = str(error)
        error_type = type(error).__name__
        context = context or {}
        
        # Classify the error
        category = self._determine_category(error_message, error_type, context)
        severity = self._determine_severity(category, error_message, context)
        
        # Generate error ID
        error_id = f"{category.value}_{int(datetime.now().timestamp())}"
        
        # Get remediation steps
        remediation_steps = self._get_remediation_steps(category, error_message, context)
        
        backup_error = BackupError(
            error_id=error_id,
            message=error_message,
            category=category,
            severity=severity,
            timestamp=datetime.now(),
            operation_id=context.get('operation_id', 'unknown'),
            repository_id=context.get('repository_id'),
            tool_name=context.get('tool_name'),
            error_code=context.get('error_code'),
            stack_trace=context.get('stack_trace'),
            context=context,
            remediation_steps=remediation_steps
        )
        
        logger.error(f"Classified backup error: {category.value} - {error_message}")
        return backup_error
    
    def create_warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> BackupWarning:
        """
        Create a backup warning with suggestions.
        
        Args:
            message: Warning message
            context: Additional context
            
        Returns:
            BackupWarning with suggestions
        """
        context = context or {}
        warning_id = f"warning_{int(datetime.now().timestamp())}"
        
        # Get suggestions based on warning message
        suggestions = self._get_warning_suggestions(message, context)
        
        warning = BackupWarning(
            warning_id=warning_id,
            message=message,
            timestamp=datetime.now(),
            operation_id=context.get('operation_id', 'unknown'),
            repository_id=context.get('repository_id'),
            severity=ErrorSeverity.LOW,
            context=context,
            suggestions=suggestions
        )
        
        logger.warning(f"Backup warning: {message}")
        return warning
    
    def _determine_category(self, error_message: str, error_type: str, 
                           context: Dict[str, Any]) -> ErrorCategory:
        """Determine the category of an error based on patterns"""
        error_message_lower = error_message.lower()
        
        # Check for network errors
        if any(pattern in error_message_lower for pattern in 
               ['connection', 'timeout', 'network', 'unreachable', 'dns']):
            return ErrorCategory.NETWORK
        
        # Check for permission errors
        if any(pattern in error_message_lower for pattern in 
               ['permission', 'denied', 'access', 'forbidden', 'unauthorized']):
            return ErrorCategory.PERMISSION
        
        # Check for resource errors
        if any(pattern in error_message_lower for pattern in 
               ['disk space', 'memory', 'quota', 'no space', 'out of memory']):
            return ErrorCategory.RESOURCE
        
        # Check for configuration errors
        if any(pattern in error_message_lower for pattern in 
               ['config', 'invalid', 'not found', 'missing', 'credential']):
            return ErrorCategory.CONFIGURATION
        
        # Check for data integrity errors
        if any(pattern in error_message_lower for pattern in 
               ['corrupt', 'checksum', 'integrity', 'verification failed']):
            return ErrorCategory.DATA_INTEGRITY
        
        # Check for transient errors
        if any(pattern in error_message_lower for pattern in 
               ['temporary', 'retry', 'busy', 'locked']):
            return ErrorCategory.TRANSIENT
        
        # Check for tool-specific errors
        if context.get('tool_name'):
            return ErrorCategory.TOOL_SPECIFIC
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, category: ErrorCategory, error_message: str,
                           context: Dict[str, Any]) -> ErrorSeverity:
        """Determine the severity of an error"""
        error_message_lower = error_message.lower()
        
        # Critical severity indicators
        if any(pattern in error_message_lower for pattern in 
               ['corrupt', 'data loss', 'critical', 'fatal']):
            return ErrorSeverity.CRITICAL
        
        # High severity for certain categories
        if category in [ErrorCategory.DATA_INTEGRITY, ErrorCategory.RESOURCE]:
            return ErrorSeverity.HIGH
        
        # Medium severity for configuration and permission issues
        if category in [ErrorCategory.CONFIGURATION, ErrorCategory.PERMISSION]:
            return ErrorSeverity.MEDIUM
        
        # Low severity for transient issues
        if category == ErrorCategory.TRANSIENT:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def _get_remediation_steps(self, category: ErrorCategory, error_message: str,
                               context: Dict[str, Any]) -> List[RemediationStep]:
        """Get remediation steps for an error category"""
        steps = []
        
        if category == ErrorCategory.NETWORK:
            steps.extend([
                RemediationStep(
                    description="Check network connectivity to the repository",
                    command="ping <repository_host>",
                    automated=False
                ),
                RemediationStep(
                    description="Verify repository URL is correct",
                    automated=False
                ),
                RemediationStep(
                    description="Check firewall settings and proxy configuration",
                    automated=False
                )
            ])
        
        elif category == ErrorCategory.PERMISSION:
            steps.extend([
                RemediationStep(
                    description="Verify credentials are correct and not expired",
                    automated=False
                ),
                RemediationStep(
                    description="Check file system permissions for backup paths",
                    command="ls -la <backup_path>",
                    automated=False
                ),
                RemediationStep(
                    description="Ensure backup user has necessary access rights",
                    automated=False
                )
            ])
        
        elif category == ErrorCategory.RESOURCE:
            steps.extend([
                RemediationStep(
                    description="Check available disk space",
                    command="df -h",
                    automated=False
                ),
                RemediationStep(
                    description="Free up disk space or increase storage capacity",
                    automated=False
                ),
                RemediationStep(
                    description="Check memory usage and available RAM",
                    command="free -h",
                    automated=False
                )
            ])
        
        elif category == ErrorCategory.CONFIGURATION:
            steps.extend([
                RemediationStep(
                    description="Verify backup configuration is valid",
                    automated=False
                ),
                RemediationStep(
                    description="Check repository configuration and credentials",
                    automated=False
                ),
                RemediationStep(
                    description="Review backup tool configuration settings",
                    automated=False
                )
            ])
        
        elif category == ErrorCategory.DATA_INTEGRITY:
            steps.extend([
                RemediationStep(
                    description="Run repository integrity check",
                    command="timelocker repository check <repository_id>",
                    automated=False
                ),
                RemediationStep(
                    description="Review backup logs for corruption indicators",
                    automated=False
                ),
                RemediationStep(
                    description="Consider repository repair if available",
                    automated=False
                )
            ])
        
        elif category == ErrorCategory.TRANSIENT:
            steps.extend([
                RemediationStep(
                    description="Retry the operation (automatic retry will be attempted)",
                    automated=True
                ),
                RemediationStep(
                    description="Wait a few minutes and try again if automatic retry fails",
                    automated=False
                )
            ])
        
        elif category == ErrorCategory.TOOL_SPECIFIC:
            tool_name = context.get('tool_name', 'backup tool')
            steps.extend([
                RemediationStep(
                    description=f"Check {tool_name} documentation for this error",
                    automated=False
                ),
                RemediationStep(
                    description=f"Verify {tool_name} is properly installed and up to date",
                    automated=False
                )
            ])
        
        else:
            steps.extend([
                RemediationStep(
                    description="Review backup logs for more details",
                    automated=False
                ),
                RemediationStep(
                    description="Contact support if the issue persists",
                    automated=False
                )
            ])
        
        return steps
    
    def _get_warning_suggestions(self, message: str, context: Dict[str, Any]) -> List[str]:
        """Get suggestions for a warning"""
        suggestions = []
        message_lower = message.lower()
        
        if 'slow' in message_lower or 'performance' in message_lower:
            suggestions.extend([
                "Consider enabling parallel processing if supported by your backup tool",
                "Check network bandwidth and system resources",
                "Review data selection rules to exclude unnecessary files"
            ])
        
        if 'skip' in message_lower or 'exclude' in message_lower:
            suggestions.extend([
                "Review data selection rules to ensure intended files are included",
                "Check file permissions for skipped files",
                "Verify file paths are correct"
            ])
        
        if 'deprecated' in message_lower:
            suggestions.extend([
                "Update configuration to use recommended settings",
                "Review documentation for migration guidance"
            ])
        
        return suggestions
    
    def _initialize_error_patterns(self) -> Dict[str, List[str]]:
        """Initialize error pattern database"""
        return {
            'network': ['connection', 'timeout', 'network', 'unreachable', 'dns'],
            'permission': ['permission', 'denied', 'access', 'forbidden', 'unauthorized'],
            'resource': ['disk space', 'memory', 'quota', 'no space', 'out of memory'],
            'configuration': ['config', 'invalid', 'not found', 'missing', 'credential'],
            'data_integrity': ['corrupt', 'checksum', 'integrity', 'verification failed'],
            'transient': ['temporary', 'retry', 'busy', 'locked']
        }
    
    def _initialize_remediation_database(self) -> Dict[str, List[RemediationStep]]:
        """Initialize remediation step database"""
        return {}
