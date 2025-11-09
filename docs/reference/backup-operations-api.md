# Backup Operations API Reference

**Status**: Active  
**Last Updated**: 2025-11-09  
**Related Specs**: [Backup Operations](.kiro/specs/backup-operations/)

## Overview

The Backup Operations API provides a comprehensive interface for orchestrating and executing backup jobs across different backup tools and storage backends. This document describes the core interfaces, data models, and usage patterns for the backup orchestration system.

## Core Components

### BackupOrchestrator

The central component that coordinates backup job execution and integrates with external systems.

#### Class Definition

```python
class BackupOrchestrator:
    """
    Orchestrates backup job execution across different backup tools.
    
    This class serves as the main entry point for backup operations,
    coordinating job validation, execution, monitoring, and error handling.
    """
    
    def __init__(
        self,
        tool_manager: ToolManager,
        progress_monitor: ProgressMonitor,
        error_handler: ErrorHandler,
        policy_service: Optional[PolicyService] = None,
        data_selection_service: Optional[DataSelectionService] = None
    ):
        """
        Initialize the backup orchestrator.
        
        Args:
            tool_manager: Manager for backup tool integration
            progress_monitor: Monitor for tracking backup progress
            error_handler: Handler for backup errors and retries
            policy_service: Optional policy management integration
            data_selection_service: Optional data selection integration
        """
```

#### Methods

##### execute_backup_job

```python
def execute_backup_job(
    self,
    job_config: BackupJobConfig
) -> BackupResult:
    """
    Execute a backup job with full orchestration.
    
    This method handles the complete backup workflow including:
    - Job configuration validation
    - Tool capability verification
    - Data selection integration
    - Progress monitoring
    - Error handling and retries
    
    Args:
        job_config: Configuration for the backup job
        
    Returns:
        BackupResult containing execution status and metrics
        
    Raises:
        ValidationError: If job configuration is invalid
        ToolNotAvailableError: If required backup tool is not available
        BackupExecutionError: If backup execution fails after retries
        
    Example:
        >>> orchestrator = BackupOrchestrator(tool_manager, monitor, handler)
        >>> config = BackupJobConfig(
        ...     job_id="backup-001",
        ...     policy_id="daily-backup",
        ...     repository_id="repo-main",
        ...     tool_type="restic"
        ... )
        >>> result = orchestrator.execute_backup_job(config)
        >>> print(f"Backup completed: {result.snapshot_id}")
    """
```

##### validate_job_configuration

```python
def validate_job_configuration(
    self,
    job_config: BackupJobConfig
) -> ValidationResult:
    """
    Validate job configuration against tool capabilities.
    
    Performs comprehensive validation including:
    - Repository accessibility
    - Tool capability compatibility
    - Data selection rule validation
    - Policy configuration verification
    
    Args:
        job_config: Configuration to validate
        
    Returns:
        ValidationResult with validation status and any issues found
        
    Example:
        >>> result = orchestrator.validate_job_configuration(config)
        >>> if not result.is_valid:
        ...     for error in result.errors:
        ...         print(f"Validation error: {error}")
    """
```

##### get_execution_status

```python
def get_execution_status(
    self,
    job_id: str
) -> ExecutionStatus:
    """
    Get current status of a running backup job.
    
    Args:
        job_id: Unique identifier for the backup job
        
    Returns:
        ExecutionStatus with current job state and progress
        
    Raises:
        JobNotFoundError: If job_id does not exist
        
    Example:
        >>> status = orchestrator.get_execution_status("backup-001")
        >>> print(f"Progress: {status.progress_percentage}%")
        >>> print(f"Files processed: {status.files_processed}")
    """
```

### JobExecutor

Handles the actual execution of backup operations with retry logic and error handling.

#### Class Definition

```python
class JobExecutor:
    """
    Executes backup jobs with retry logic and error handling.
    
    This class manages the direct interaction with backup tools,
    implementing retry strategies and error classification.
    """
    
    def __init__(
        self,
        tool_manager: ToolManager,
        retry_handler: RetryHandler,
        max_retries: int = 3
    ):
        """
        Initialize the job executor.
        
        Args:
            tool_manager: Manager for backup tool operations
            retry_handler: Handler for retry logic
            max_retries: Maximum number of retry attempts (default: 3)
        """
```

#### Methods

##### execute_with_retry

```python
def execute_with_retry(
    self,
    job: BackupJob,
    max_retries: Optional[int] = None
) -> ExecutionResult:
    """
    Execute backup job with configurable retry logic.
    
    Implements exponential backoff retry strategy for transient errors.
    Permanent errors result in immediate failure without retry.
    
    Args:
        job: Backup job to execute
        max_retries: Override default maximum retry attempts
        
    Returns:
        ExecutionResult with final execution status
        
    Raises:
        BackupExecutionError: If all retry attempts fail
        
    Example:
        >>> executor = JobExecutor(tool_manager, retry_handler)
        >>> result = executor.execute_with_retry(job, max_retries=5)
        >>> if result.success:
        ...     print(f"Backup succeeded on attempt {result.attempt_number}")
    """
```

##### handle_execution_error

```python
def handle_execution_error(
    self,
    error: BackupError,
    attempt: int
) -> RetryDecision:
    """
    Determine retry strategy based on error type and attempt count.
    
    Classifies errors as transient or permanent and determines
    appropriate retry behavior.
    
    Args:
        error: The error that occurred during execution
        attempt: Current attempt number (1-indexed)
        
    Returns:
        RetryDecision indicating whether to retry and delay duration
        
    Example:
        >>> decision = executor.handle_execution_error(error, attempt=2)
        >>> if decision.should_retry:
        ...     time.sleep(decision.delay_seconds)
        ...     # Retry the operation
    """
```

### ToolManager

Manages backup tool integration and capability detection.

#### Class Definition

```python
class ToolManager:
    """
    Manages backup tool integration and capabilities.
    
    Provides unified interface for working with different backup tools,
    handling capability detection, configuration, and optimization.
    """
    
    def __init__(
        self,
        plugin_registry: PluginRegistry,
        capability_checker: CapabilityChecker
    ):
        """
        Initialize the tool manager.
        
        Args:
            plugin_registry: Registry of available backup tool plugins
            capability_checker: Checker for tool capability detection
        """
```

#### Methods

##### get_tool_capabilities

```python
def get_tool_capabilities(
    self,
    tool_type: str
) -> ToolCapabilities:
    """
    Get comprehensive capability information for a backup tool.
    
    Returns detailed information about native and wrapper-provided
    capabilities for the specified tool.
    
    Args:
        tool_type: Type of backup tool (e.g., "restic", "borg")
        
    Returns:
        ToolCapabilities with feature information
        
    Raises:
        ToolNotFoundError: If tool_type is not supported
        
    Example:
        >>> capabilities = tool_manager.get_tool_capabilities("restic")
        >>> print(f"Native features: {capabilities.native_features}")
        >>> print(f"Wrapper features: {capabilities.wrapper_features}")
        >>> if Feature.PARALLEL_PROCESSING in capabilities.native_features:
        ...     print("Tool supports parallel processing natively")
    """
```

##### configure_tool_for_job

```python
def configure_tool_for_job(
    self,
    tool: BackupTool,
    job: BackupJob
) -> ToolConfiguration:
    """
    Configure backup tool for optimal job execution.
    
    Analyzes job requirements and system resources to determine
    optimal tool configuration parameters.
    
    Args:
        tool: Backup tool instance to configure
        job: Backup job to configure for
        
    Returns:
        ToolConfiguration with optimized settings
        
    Example:
        >>> config = tool_manager.configure_tool_for_job(restic_tool, job)
        >>> print(f"Parallel operations: {config.parallel_operations}")
        >>> print(f"Memory limit: {config.memory_limit_mb}MB")
    """
```

##### get_supported_tools

```python
def get_supported_tools(self) -> List[ToolInfo]:
    """
    Get list of all supported backup tools with capability summaries.
    
    Returns:
        List of ToolInfo objects describing available tools
        
    Example:
        >>> tools = tool_manager.get_supported_tools()
        >>> for tool in tools:
        ...     print(f"{tool.name} v{tool.version}")
        ...     print(f"  Features: {', '.join(tool.feature_summary)}")
    """
```

### ProgressMonitor

Tracks and reports backup execution progress in real-time.

#### Class Definition

```python
class ProgressMonitor:
    """
    Monitors and reports backup execution progress.
    
    Provides real-time progress tracking with configurable update
    intervals and notification integration.
    """
    
    def __init__(
        self,
        notification_service: Optional[NotificationService] = None,
        update_interval: int = 5
    ):
        """
        Initialize the progress monitor.
        
        Args:
            notification_service: Optional service for progress notifications
            update_interval: Seconds between progress updates (default: 5)
        """
```

#### Methods

##### start_monitoring

```python
def start_monitoring(
    self,
    job_id: str,
    estimated_size: int
) -> None:
    """
    Start monitoring progress for a backup job.
    
    Args:
        job_id: Unique identifier for the job
        estimated_size: Estimated total size in bytes
        
    Example:
        >>> monitor.start_monitoring("backup-001", estimated_size=1024*1024*1024)
    """
```

##### update_progress

```python
def update_progress(
    self,
    job_id: str,
    progress_data: ProgressData
) -> None:
    """
    Update progress information for active job.
    
    Args:
        job_id: Job identifier
        progress_data: Current progress metrics
        
    Example:
        >>> progress = ProgressData(
        ...     files_processed=150,
        ...     bytes_transferred=512*1024*1024,
        ...     current_file="/path/to/file.txt"
        ... )
        >>> monitor.update_progress("backup-001", progress)
    """
```

##### get_progress_report

```python
def get_progress_report(
    self,
    job_id: str
) -> ProgressReport:
    """
    Get comprehensive progress report for job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        ProgressReport with detailed metrics
        
    Example:
        >>> report = monitor.get_progress_report("backup-001")
        >>> print(f"Progress: {report.percentage_complete}%")
        >>> print(f"ETA: {report.estimated_completion_time}")
        >>> print(f"Throughput: {report.bytes_per_second / 1024 / 1024:.2f} MB/s")
    """
```

## Data Models

### BackupJobConfig

Configuration for a backup job execution.

```python
@dataclass
class BackupJobConfig:
    """Configuration for a backup job execution."""
    
    job_id: str
    """Unique identifier for the job"""
    
    policy_id: str
    """ID of the backup policy to apply"""
    
    repository_id: str
    """ID of the target repository"""
    
    data_selection_id: str
    """ID of the data selection configuration"""
    
    tool_type: str
    """Type of backup tool to use (e.g., 'restic', 'borg')"""
    
    execution_mode: ExecutionMode
    """Execution mode (on_demand, scheduled, manual_retry)"""
    
    retry_config: RetryConfig
    """Configuration for retry behavior"""
    
    notification_config: NotificationConfig
    """Configuration for notifications"""
    
    tags: Optional[List[str]] = None
    """Optional tags for the backup snapshot"""
```

### BackupResult

Result of backup job execution.

```python
@dataclass
class BackupResult:
    """Result of backup job execution."""
    
    job_id: str
    """Job identifier"""
    
    status: BackupStatus
    """Final execution status"""
    
    snapshot_id: Optional[str]
    """ID of created snapshot (if successful)"""
    
    files_processed: int
    """Number of files processed"""
    
    bytes_transferred: int
    """Total bytes transferred"""
    
    duration: timedelta
    """Total execution duration"""
    
    errors: List[BackupError]
    """List of errors encountered"""
    
    warnings: List[BackupWarning]
    """List of warnings generated"""
    
    performance_metrics: PerformanceMetrics
    """Performance metrics for the operation"""
```

### ToolCapabilities

Comprehensive capability information for a backup tool.

```python
@dataclass
class ToolCapabilities:
    """Comprehensive capability information for a backup tool."""
    
    tool_name: str
    """Name of the backup tool"""
    
    version: str
    """Tool version"""
    
    native_features: Set[Feature]
    """Features natively supported by the tool"""
    
    wrapper_features: Set[Feature]
    """Features provided by plugin wrapper"""
    
    limitations: List[Limitation]
    """Known limitations of the tool"""
    
    performance_characteristics: PerformanceProfile
    """Performance profile information"""
```

### ExecutionStatus

Current status of a running backup job.

```python
@dataclass
class ExecutionStatus:
    """Current status of a running backup job."""
    
    job_id: str
    """Job identifier"""
    
    status: BackupStatus
    """Current execution status"""
    
    progress_percentage: float
    """Completion percentage (0-100)"""
    
    files_processed: int
    """Files processed so far"""
    
    bytes_transferred: int
    """Bytes transferred so far"""
    
    current_file: Optional[str]
    """Currently processing file"""
    
    estimated_completion: Optional[datetime]
    """Estimated completion time"""
    
    throughput: float
    """Current throughput in bytes/second"""
```

## Enumerations

### BackupStatus

```python
class BackupStatus(Enum):
    """Backup job execution status."""
    PENDING = "pending"
    VALIDATING = "validating"
    PREPARING = "preparing"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### ExecutionMode

```python
class ExecutionMode(Enum):
    """Backup execution mode."""
    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    MANUAL_RETRY = "manual_retry"
```

### Feature

```python
class Feature(Enum):
    """Backup tool features."""
    PARALLEL_PROCESSING = "parallel_processing"
    INTEGRITY_VALIDATION = "integrity_validation"
    INCREMENTAL_BACKUP = "incremental_backup"
    COMPRESSION = "compression"
    ENCRYPTION = "encryption"
    DEDUPLICATION = "deduplication"
    RESUME_SUPPORT = "resume_support"
    BANDWIDTH_LIMITING = "bandwidth_limiting"
```

## Error Handling

### Exception Hierarchy

```python
class BackupOperationError(Exception):
    """Base exception for backup operations."""
    pass

class ValidationError(BackupOperationError):
    """Raised when job configuration validation fails."""
    pass

class ToolNotAvailableError(BackupOperationError):
    """Raised when required backup tool is not available."""
    pass

class BackupExecutionError(BackupOperationError):
    """Raised when backup execution fails."""
    pass

class JobNotFoundError(BackupOperationError):
    """Raised when job ID does not exist."""
    pass
```

### Error Context

All exceptions include detailed context information:

```python
try:
    result = orchestrator.execute_backup_job(config)
except BackupExecutionError as e:
    print(f"Backup failed: {e}")
    print(f"Job ID: {e.job_id}")
    print(f"Attempt: {e.attempt_number}")
    print(f"Error type: {e.error_type}")
    print(f"Suggested action: {e.suggested_action}")
```

## Usage Examples

### Basic Backup Execution

```python
from TimeLocker.services.backup_orchestrator import BackupOrchestrator
from TimeLocker.interfaces.data_models import BackupJobConfig, ExecutionMode

# Initialize orchestrator
orchestrator = BackupOrchestrator(
    tool_manager=tool_manager,
    progress_monitor=progress_monitor,
    error_handler=error_handler
)

# Configure backup job
config = BackupJobConfig(
    job_id="daily-backup-001",
    policy_id="daily-documents",
    repository_id="main-repo",
    data_selection_id="documents-selection",
    tool_type="restic",
    execution_mode=ExecutionMode.ON_DEMAND,
    retry_config=RetryConfig(max_retries=3, base_delay=2),
    notification_config=NotificationConfig(on_success=True, on_failure=True)
)

# Execute backup
result = orchestrator.execute_backup_job(config)

if result.status == BackupStatus.COMPLETED:
    print(f"Backup successful! Snapshot: {result.snapshot_id}")
    print(f"Files: {result.files_processed}, Size: {result.bytes_transferred}")
else:
    print(f"Backup failed: {result.errors}")
```

### Progress Monitoring

```python
import time
from threading import Thread

def monitor_progress(orchestrator, job_id):
    """Monitor backup progress in separate thread."""
    while True:
        status = orchestrator.get_execution_status(job_id)
        print(f"Progress: {status.progress_percentage:.1f}%")
        print(f"Files: {status.files_processed}")
        print(f"Throughput: {status.throughput / 1024 / 1024:.2f} MB/s")
        
        if status.status in [BackupStatus.COMPLETED, BackupStatus.FAILED]:
            break
            
        time.sleep(5)

# Start monitoring in background
monitor_thread = Thread(target=monitor_progress, args=(orchestrator, job_id))
monitor_thread.start()

# Execute backup
result = orchestrator.execute_backup_job(config)

# Wait for monitoring to complete
monitor_thread.join()
```

### Tool Capability Check

```python
# Check tool capabilities before execution
capabilities = tool_manager.get_tool_capabilities("restic")

print(f"Tool: {capabilities.tool_name} v{capabilities.version}")
print(f"Native features: {capabilities.native_features}")
print(f"Wrapper features: {capabilities.wrapper_features}")

if Feature.PARALLEL_PROCESSING in capabilities.native_features:
    print("Parallel processing is natively supported")
    
for limitation in capabilities.limitations:
    print(f"Limitation: {limitation.description}")
```

## Integration Points

### Policy Management Integration

```python
# Orchestrator automatically integrates with policy service
orchestrator = BackupOrchestrator(
    tool_manager=tool_manager,
    progress_monitor=progress_monitor,
    error_handler=error_handler,
    policy_service=policy_service  # Policy integration
)

# Policy is automatically retrieved and applied
config = BackupJobConfig(
    job_id="backup-001",
    policy_id="daily-backup",  # Policy ID reference
    # ... other config
)
```

### Data Selection Integration

```python
# Data selection is automatically retrieved and applied
config = BackupJobConfig(
    job_id="backup-001",
    policy_id="daily-backup",
    data_selection_id="documents-selection",  # Selection ID reference
    # ... other config
)

# Selection rules are translated to tool-specific format
result = orchestrator.execute_backup_job(config)
```

## Performance Optimization

### Parallel Processing Configuration

```python
# Tool manager automatically optimizes parallelism
config = tool_manager.configure_tool_for_job(tool, job)

print(f"Parallel operations: {config.parallel_operations}")
print(f"Memory limit: {config.memory_limit_mb}MB")
print(f"I/O priority: {config.io_priority}")
```

### Resource Monitoring

```python
# Access performance metrics from result
result = orchestrator.execute_backup_job(config)

metrics = result.performance_metrics
print(f"Average throughput: {metrics.avg_throughput_mbps:.2f} MB/s")
print(f"Peak memory: {metrics.peak_memory_mb:.2f} MB")
print(f"CPU utilization: {metrics.avg_cpu_percent:.1f}%")
```

## See Also

- [Backup Operations Design](.kiro/specs/backup-operations/design.md)
- [Backup Operations Requirements](.kiro/specs/backup-operations/requirements.md)
- [Plugin Wrapper Development Guide](../guides/developer/plugin-wrapper-development.md)
- [Backup Operations Troubleshooting](../guides/user/backup-operations-troubleshooting.md)
