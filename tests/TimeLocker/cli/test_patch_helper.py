"""
Helper module for consistent test patching across CLI tests.

This module provides standardized patch paths and helper functions to ensure
tests correctly mock the CLI service layer regardless of refactoring.
"""

# Correct patch paths for CLI service integration
SERVICE_MANAGER_PATCH_PATH = 'TimeLocker.cli_modules.helpers.service_helpers._get_service_manager_for_command'
CREDENTIAL_MANAGER_PATCH_PATH = 'TimeLocker.security.credential_manager.CredentialManager'
CONFIGURATION_MODULE_PATCH_PATH = 'TimeLocker.config.configuration_module.ConfigurationModule'
BACKUP_MANAGER_PATCH_PATH = 'TimeLocker.backup_manager.BackupManager'


def get_service_manager_patch_path() -> str:
    """
    Get the correct patch path for _get_service_manager_for_command.
    
    Returns:
        str: Full module path for patching service manager
    """
    return SERVICE_MANAGER_PATCH_PATH


def get_credential_manager_patch_path() -> str:
    """
    Get the correct patch path for CredentialManager.
    
    Returns:
        str: Full module path for patching credential manager
    """
    return CREDENTIAL_MANAGER_PATCH_PATH


def get_configuration_module_patch_path() -> str:
    """
    Get the correct patch path for ConfigurationModule.
    
    Returns:
        str: Full module path for patching configuration module
    """
    return CONFIGURATION_MODULE_PATCH_PATH


def get_backup_manager_patch_path() -> str:
    """
    Get the correct patch path for BackupManager.
    
    Returns:
        str: Full module path for patching backup manager
    """
    return BACKUP_MANAGER_PATCH_PATH
