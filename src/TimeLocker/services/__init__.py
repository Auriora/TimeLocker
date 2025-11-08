"""
Services module for TimeLocker

This module provides service implementations for repository management,
validation, and other core functionality.
"""

from .repository_manager import RepositoryManager
from .repository_factory import RepositoryFactory
from .repository_service import RepositoryService
from .repository_state_manager import RepositoryStateManager
from .existing_repository_handler import ExistingRepositoryHandler
from .validation_service import ValidationService
from .repository_credential_manager import RepositoryCredentialManager
from .s3_service_manager import S3ServiceManager
from .repository_performance_monitor import (
    RepositoryPerformanceMonitor,
    PerformanceThresholds,
    PerformanceMetric,
    PerformanceWarning
)
from .repository_concurrency_manager import (
    RepositoryConcurrencyManager,
    LockInfo,
    ConcurrencyStats
)
from .repository_cache_manager import (
    RepositoryCacheManager,
    LazyRepositoryLoader,
    CacheEntry,
    CacheStatistics
)
from .plugin_registry import PluginRegistry, get_plugin_registry
from .plugin_initializer import (
    initialize_plugins,
    get_available_engines_info,
    check_engine_availability,
    get_engines_for_storage,
    print_plugin_status
)
from .job_executor import (
    JobExecutor,
    ErrorClassifier,
    ErrorCategory,
    RetryStrategy,
    ErrorClassification,
    RetryDecision,
    ExecutionResult
)
from .tool_manager import (
    ToolManager,
    ToolCapabilities,
    ToolInfo,
    Feature,
    Limitation,
    PerformanceProfile
)
from .plugin_wrapper import (
    PluginWrapper,
    BackupConfig,
    PluginWrapperError,
    CapabilityNotSupportedError
)
from .restic_plugin_wrapper import ResticPluginWrapper
from .wrapper_registry import (
    WrapperRegistry,
    get_wrapper_registry,
    initialize_wrappers
)

__all__ = [
    'RepositoryManager',
    'RepositoryFactory', 
    'RepositoryService',
    'RepositoryStateManager',
    'ExistingRepositoryHandler',
    'ValidationService',
    'RepositoryCredentialManager',
    'S3ServiceManager',
    'RepositoryPerformanceMonitor',
    'PerformanceThresholds',
    'PerformanceMetric',
    'PerformanceWarning',
    'RepositoryConcurrencyManager',
    'LockInfo',
    'ConcurrencyStats',
    'RepositoryCacheManager',
    'LazyRepositoryLoader',
    'CacheEntry',
    'CacheStatistics',
    'PluginRegistry',
    'get_plugin_registry',
    'initialize_plugins',
    'get_available_engines_info',
    'check_engine_availability',
    'get_engines_for_storage',
    'print_plugin_status',
    'JobExecutor',
    'ErrorClassifier',
    'ErrorCategory',
    'RetryStrategy',
    'ErrorClassification',
    'RetryDecision',
    'ExecutionResult',
    'ToolManager',
    'ToolCapabilities',
    'ToolInfo',
    'Feature',
    'Limitation',
    'PerformanceProfile',
    'PluginWrapper',
    'BackupConfig',
    'PluginWrapperError',
    'CapabilityNotSupportedError',
    'ResticPluginWrapper',
    'WrapperRegistry',
    'get_wrapper_registry',
    'initialize_wrappers'
]