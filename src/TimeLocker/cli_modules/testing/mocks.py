"""
Mock service factories for CLI command testing.

Provides factory functions for creating properly configured mock services
that match the actual service interfaces used by CLI commands.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock
from pathlib import Path


class MockServiceFactory:
    """
    Factory for creating mock services with consistent configurations.
    
    This class provides a centralized way to create mock services that
    match the actual service interfaces, ensuring tests are consistent
    and maintainable.
    """
    
    @staticmethod
    def create_service_manager(
        repositories: Optional[List[Dict[str, Any]]] = None,
        snapshots: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Mock:
        """
        Create a mock service manager.
        
        Args:
            repositories: List of mock repositories
            snapshots: List of mock snapshots
            **kwargs: Additional service manager properties
        
        Returns:
            Mock service manager
        """
        return create_mock_service_manager(
            repositories=repositories,
            snapshots=snapshots,
            **kwargs
        )
    
    @staticmethod
    def create_config_service(
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Mock:
        """
        Create a mock config service.
        
        Args:
            config: Mock configuration data
            **kwargs: Additional config service properties
        
        Returns:
            Mock config service
        """
        return create_mock_config_service(config=config, **kwargs)
    
    @staticmethod
    def create_repository_resolver(
        repositories: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Mock:
        """
        Create a mock repository resolver.
        
        Args:
            repositories: Dictionary of repository name to repository data
            **kwargs: Additional resolver properties
        
        Returns:
            Mock repository resolver
        """
        return create_mock_repository_resolver(repositories=repositories, **kwargs)
    
    @staticmethod
    def create_service_facade(**kwargs) -> Mock:
        """
        Create a mock service facade.
        
        Args:
            **kwargs: Service facade properties
        
        Returns:
            Mock service facade
        """
        return create_mock_service_facade(**kwargs)


def create_mock_service_manager(
    repositories: Optional[List[Dict[str, Any]]] = None,
    snapshots: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> Mock:
    """
    Create a properly structured mock service manager.
    
    This creates a mock that matches the actual CLIServiceManager structure
    with repository_service, snapshot_service, config_module, recovery_service,
    selection_service, monitoring_service, and credential_service properties.
    
    Args:
        repositories: List of mock repositories to return
        snapshots: List of mock snapshots to return
        **kwargs: Additional service manager properties
    
    Returns:
        Mock service manager with configured services
    """
    mock_manager = Mock()
    
    # Repository service
    mock_manager.repository_service = Mock()
    mock_manager.repository_service.list_repositories.return_value = repositories or []
    mock_manager.repository_service.get_repository.return_value = None
    mock_manager.repository_service.add_repository.return_value = {'success': True}
    mock_manager.repository_service.remove_repository.return_value = {'success': True}
    mock_manager.repository_service.update_repository.return_value = {'success': True}
    mock_manager.repository_service.initialize_repository.return_value = {
        'success': True,
        'already_initialized': False
    }
    mock_manager.repository_service.check_repository.return_value = {'success': True}
    mock_manager.repository_service.get_repository_stats.return_value = {
        'size': 1024,
        'snapshots': 5,
        'total_file_count': 100
    }
    mock_manager.repository_service.set_default_repository.return_value = None
    
    # Snapshot service
    mock_manager.snapshot_service = Mock()
    mock_manager.snapshot_service.list_snapshots.return_value = snapshots or []
    mock_manager.snapshot_service.get_snapshot.return_value = None
    mock_manager.snapshot_service.find_snapshots.return_value = []
    mock_manager.snapshot_service.delete_snapshot.return_value = {'success': True}
    
    # Config module
    mock_manager.config_module = Mock()
    mock_manager.config_module.get_repository.return_value = None
    mock_manager.config_module.list_repositories.return_value = repositories or []
    mock_manager.config_module.set_repository.return_value = None
    mock_manager.config_module.remove_repository.return_value = None
    
    # Backup orchestrator
    mock_manager.backup_orchestrator = Mock()
    mock_manager.backup_orchestrator.execute_backup.return_value = Mock(
        success=True,
        snapshot_id="test123abc"
    )
    
    # Configuration service
    mock_manager.configuration_service = Mock()
    
    # Recovery service (for restore commands)
    mock_manager.recovery_service = Mock()
    mock_manager.recovery_service.restore_files.return_value = {'success': True}
    mock_manager.recovery_service.restore_full.return_value = {'success': True}
    mock_manager.recovery_service.browse_snapshot.return_value = []
    mock_manager.recovery_service.mount_snapshot.return_value = {'success': True, 'mount_point': '/tmp/mount'}
    mock_manager.recovery_service.unmount_snapshot.return_value = {'success': True}
    
    # Selection service (for data selection commands)
    mock_manager.selection_service = Mock()
    mock_template = Mock()
    mock_template.name = "test-template"
    mock_template.patterns = []
    mock_manager.selection_service.get_template.return_value = mock_template
    mock_manager.selection_service.save_template.return_value = None
    mock_manager.selection_service.list_templates.return_value = []
    mock_manager.selection_service.delete_template.return_value = None
    mock_manager.selection_service.validate_template.return_value = {'valid': True, 'errors': []}
    
    # Monitoring service (for monitoring commands)
    mock_manager.monitoring_service = Mock()
    mock_manager.monitoring_service.get_health.return_value = {'status': 'healthy'}
    mock_manager.monitoring_service.get_stats.return_value = {'backups': 10, 'total_size': 1024}
    mock_manager.monitoring_service.get_backup_history.return_value = []
    mock_manager.monitoring_service.get_performance_metrics.return_value = {}
    
    # Credential service (for credential commands)
    mock_manager.credential_service = Mock()
    mock_manager.credential_service.store_credentials.return_value = None
    mock_manager.credential_service.get_credentials.return_value = {'password': 'test_password'}
    mock_manager.credential_service.remove_credentials.return_value = None
    mock_manager.credential_service.list_credentials.return_value = []
    mock_manager.credential_service.has_credentials.return_value = True
    
    # Direct method access for CLI commands
    mock_manager.list_repositories = mock_manager.repository_service.list_repositories
    mock_manager.get_repository = mock_manager.repository_service.get_repository
    mock_manager.add_repository = mock_manager.repository_service.add_repository
    mock_manager.remove_repository = mock_manager.repository_service.remove_repository
    mock_manager.update_repository = mock_manager.repository_service.update_repository
    mock_manager.initialize_repository = mock_manager.repository_service.initialize_repository
    mock_manager.check_repository = mock_manager.repository_service.check_repository
    mock_manager.get_repository_stats = mock_manager.repository_service.get_repository_stats
    mock_manager.list_snapshots = mock_manager.snapshot_service.list_snapshots
    mock_manager.get_snapshot = mock_manager.snapshot_service.get_snapshot
    mock_manager.find_snapshots = mock_manager.snapshot_service.find_snapshots
    
    # Apply any additional properties
    for key, value in kwargs.items():
        setattr(mock_manager, key, value)
    
    return mock_manager


def create_mock_config_service(
    config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Mock:
    """
    Create a mock ConfigService.
    
    Args:
        config: Mock configuration data
        **kwargs: Additional config service properties
    
    Returns:
        Mock config service
    """
    mock_service = Mock()
    
    if config is None:
        config = {
            'version': '1.0',
            'repositories': [],
            'targets': [],
            'policies': [],
            'settings': {}
        }
    
    mock_service.get_config.return_value = config
    mock_service.get_repository_config.return_value = None
    mock_service.get_policy_config.return_value = None
    mock_service.validate_config.return_value = {'valid': True, 'errors': []}
    mock_service.reload_config.return_value = None
    
    # Apply any additional properties
    for key, value in kwargs.items():
        setattr(mock_service, key, value)
    
    return mock_service


def create_mock_repository_resolver(
    repositories: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Mock:
    """
    Create a mock RepositoryResolver.
    
    Args:
        repositories: Dictionary mapping repository names to repository data
        **kwargs: Additional resolver properties
    
    Returns:
        Mock repository resolver
    """
    mock_resolver = Mock()
    
    if repositories is None:
        repositories = {}
    
    def resolve_repository(name_or_path: str):
        """Mock resolve_repository implementation."""
        return repositories.get(name_or_path)
    
    mock_resolver.resolve_repository.side_effect = resolve_repository
    mock_resolver.resolve_credentials.return_value = {'password': 'test_password'}
    mock_resolver.detect_backend.return_value = 'local'
    mock_resolver.validate_repository.return_value = {'valid': True, 'errors': []}
    
    # Apply any additional properties
    for key, value in kwargs.items():
        setattr(mock_resolver, key, value)
    
    return mock_resolver


def create_mock_service_facade(**kwargs) -> Mock:
    """
    Create a mock ServiceFacade.
    
    Args:
        **kwargs: Service facade properties
    
    Returns:
        Mock service facade
    """
    mock_facade = Mock()
    
    # Service getters
    mock_facade.get_backup_service.return_value = Mock()
    mock_facade.get_restore_service.return_value = Mock()
    mock_facade.get_repository_service.return_value = Mock()
    mock_facade.get_snapshot_service.return_value = Mock()
    mock_facade.get_policy_service.return_value = Mock()
    
    # Service management
    mock_facade.initialize_services.return_value = None
    mock_facade.health_check.return_value = {'healthy': True, 'services': {}}
    
    # Apply any additional properties
    for key, value in kwargs.items():
        setattr(mock_facade, key, value)
    
    return mock_facade


def create_mock_prompt_service(
    responses: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Mock:
    """
    Create a mock PromptService.
    
    Args:
        responses: Dictionary mapping prompt types to responses
        **kwargs: Additional prompt service properties
    
    Returns:
        Mock prompt service
    """
    mock_service = Mock()
    
    if responses is None:
        responses = {}
    
    mock_service.prompt_text.return_value = responses.get('text', 'test-input')
    mock_service.prompt_choice.return_value = responses.get('choice', 'option1')
    mock_service.prompt_confirm.return_value = responses.get('confirm', True)
    mock_service.prompt_password.return_value = responses.get('password', 'test_password')
    
    # Apply any additional properties
    for key, value in kwargs.items():
        setattr(mock_service, key, value)
    
    return mock_service


def create_mock_output_formatter(**kwargs) -> Mock:
    """
    Create a mock OutputFormatter.
    
    Args:
        **kwargs: Output formatter properties
    
    Returns:
        Mock output formatter
    """
    mock_formatter = Mock()
    
    mock_formatter.format_table.return_value = "Formatted Table"
    mock_formatter.format_panel.return_value = "Formatted Panel"
    mock_formatter.format_json.return_value = '{"formatted": "json"}'
    mock_formatter.format_error.return_value = "Formatted Error"
    
    # Apply any additional properties
    for key, value in kwargs.items():
        setattr(mock_formatter, key, value)
    
    return mock_formatter


def create_mock_progress_service(**kwargs) -> Mock:
    """
    Create a mock ProgressService.
    
    Args:
        **kwargs: Progress service properties
    
    Returns:
        Mock progress service
    """
    mock_service = Mock()
    
    mock_progress = Mock()
    mock_progress.update.return_value = None
    mock_progress.advance.return_value = None
    mock_progress.finish.return_value = None
    
    mock_service.create_progress.return_value = mock_progress
    mock_service.update_progress.return_value = None
    mock_service.complete_progress.return_value = None
    
    # Context manager support
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_progress
    mock_context.__exit__.return_value = None
    mock_service.with_progress.return_value = mock_context
    
    # Apply any additional properties
    for key, value in kwargs.items():
        setattr(mock_service, key, value)
    
    return mock_service
