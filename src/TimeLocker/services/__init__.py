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
from .plugin_registry import PluginRegistry, get_plugin_registry
from .plugin_initializer import (
    initialize_plugins,
    get_available_engines_info,
    check_engine_availability,
    get_engines_for_storage,
    print_plugin_status
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
    'PluginRegistry',
    'get_plugin_registry',
    'initialize_plugins',
    'get_available_engines_info',
    'check_engine_availability',
    'get_engines_for_storage',
    'print_plugin_status'
]