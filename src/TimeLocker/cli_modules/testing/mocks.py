"""
Mock service factories for CLI command testing.

Provides factory functions for creating properly configured mock services
that match the actual service interfaces used by CLI commands.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock
from pathlib import Path
from datetime import datetime


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
    Create a properly structured mock service manager with lifecycle helpers.
    
    Args:
        repositories: Initial repository data
        snapshots: Snapshot data
        **kwargs: Extra attributes for the mock
    """
    mock_manager = Mock()

    class _RepositoryDict(dict):
        def keys(self):
            return list(super().values())

    repo_store: _RepositoryDict = _RepositoryDict()
    credential_store: Dict[str, Dict[str, Any]] = {}
    default_state = {"default_repository": None}

    for repo in repositories or []:
        if isinstance(repo, dict) and repo.get("name"):
            repo_store[repo["name"]] = dict(repo)

    def _normalize_name(*candidates: Optional[str]) -> str:
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        if default_state["default_repository"]:
            return default_state["default_repository"]
        return "test-repo"

    def _ensure_repo(name: Optional[str]) -> Dict[str, Any]:
        repo_name = _normalize_name(name)
        repo = repo_store.get(repo_name)
        if not repo:
            repo = {
                "name": repo_name,
                "uri": f"file:///tmp/{repo_name}",
                "description": "",
                "metadata": {},
                "engine": "restic",
                "status": "active",
            }
            repo_store[repo_name] = repo
            default_state.setdefault("default_repository", repo_name)
        return repo

    def _mutate_metadata(repo: Dict[str, Any]) -> Dict[str, Any]:
        repo.setdefault("metadata", {})
        return repo["metadata"]

    def _add_repository(**kwargs):
        repo = _update_repository(**kwargs)
        return repo

    def _update_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        if kwargs.get("description") is not None:
            repo["description"] = kwargs.get("description")
        if kwargs.get("metadata"):
            _mutate_metadata(repo).update(kwargs["metadata"])
        if kwargs.get("configuration"):
            for key, value in kwargs["configuration"].items():
                if key == "metadata":
                    _mutate_metadata(repo).update(value or {})
                else:
                    repo[key] = value
        if kwargs.get("uri"):
            repo["uri"] = kwargs["uri"]
        if kwargs.get("engine"):
            repo["engine"] = kwargs["engine"]
        if kwargs.get("status"):
            repo["status"] = kwargs["status"]
        return {"success": True, "repository": repo}

    def _update_repository_metadata(**kwargs):
        repo = _ensure_repo(kwargs.get("name") or kwargs.get("repository"))
        metadata = kwargs.get("metadata") or {}
        remove = kwargs.get("remove_metadata") or kwargs.get("remove_keys") or []
        clear = kwargs.get("clear_metadata") or kwargs.get("clear")
        repo_metadata = _mutate_metadata(repo)
        if clear:
            repo_metadata.clear()
        for key in remove:
            repo_metadata.pop(key, None)
        if metadata:
            repo_metadata.update(metadata)
        return {"success": True, "repository": repo}

    def _update_repository_configuration(**kwargs):
        configuration = kwargs.get("configuration", {}).copy()
        for field in ("uri", "description", "engine", "type", "password"):
            if kwargs.get(field) is not None:
                configuration[field] = kwargs[field]
        if kwargs.get("metadata"):
            configuration.setdefault("metadata", {}).update(kwargs["metadata"])
        return _update_repository(name=kwargs.get("name"), configuration=configuration)

    def _list_repositories(filters=None, **_kwargs):
        repos = list(repo_store.values())
        filters = filters or {}
        status = filters.get("status")
        engine = filters.get("engine")
        if status:
            repos = [repo for repo in repos if repo.get("status") == status]
        if engine:
            repos = [repo for repo in repos if repo.get("engine") == engine]
        return repos

    def _remove_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository"))
        repo_store.pop(name, None)
        return {"success": True}

    def _set_default_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository"))
        default_state["default_repository"] = name
        return {"success": True}

    def _clear_default_repository(**_kwargs):
        default_state["default_repository"] = None
        return {"success": True}

    def _transition_repository_state(**kwargs):
        state = kwargs.get("state") or kwargs.get("target_state") or kwargs.get("status") or "active"
        return _update_repository(name=kwargs.get("name"), status=state)

    def _rotate_credentials(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        record = credential_store.setdefault(name, {"password_history": [], "backend": {}})
        if kwargs.get("new_password") or kwargs.get("password"):
            password = kwargs.get("new_password") or kwargs.get("password")
            record["password_history"].append(password)
            repo["last_password_rotation"] = password
        backend_creds = kwargs.get("backend_credentials") or kwargs.get("credentials")
        backend_type = kwargs.get("backend_type") or kwargs.get("backend")
        if backend_creds:
            record["backend"] = {"type": backend_type, "credentials": backend_creds}
            repo["backend_credentials"] = backend_creds
        repo["last_credential_rotation"] = datetime.utcnow().isoformat()
        return {"success": True, "repository": repo, "credentials": record}

    def _rotate_repository_password(**kwargs):
        kwargs["new_password"] = kwargs.get("new_password") or kwargs.get("password")
        return _rotate_credentials(**kwargs)

    def _rotate_backend_credentials(**kwargs):
        kwargs["backend_credentials"] = kwargs.get("backend_credentials") or kwargs.get("credentials")
        return _rotate_credentials(**kwargs)

    def _simple_success(**_kwargs):
        return {"success": True}

    # Repository service wiring
    mock_manager.repository_service = MagicMock()
    mock_manager.repository_service.list_repositories.side_effect = _list_repositories
    mock_manager.repository_service.get_repository.side_effect = lambda name=None, **_kw: _ensure_repo(name)
    mock_manager.repository_service.add_repository.side_effect = _add_repository
    mock_manager.repository_service.remove_repository.side_effect = _remove_repository
    mock_manager.repository_service.update_repository.side_effect = _update_repository
    mock_manager.repository_service.update_repository_metadata.side_effect = _update_repository_metadata
    mock_manager.repository_service.update_repository_configuration.side_effect = _update_repository_configuration
    mock_manager.repository_service.initialize_repository.side_effect = lambda **_kw: {
        "success": True,
        "already_initialized": False,
    }
    mock_manager.repository_service.check_repository.side_effect = lambda **_kw: {"success": True}
    mock_manager.repository_service.get_repository_stats.side_effect = lambda **_kw: {
        "size": 1024,
        "snapshots": 5,
        "total_file_count": 100,
    }
    mock_manager.repository_service.set_default_repository.side_effect = _set_default_repository
    mock_manager.repository_service.clear_default_repository.side_effect = _clear_default_repository
    mock_manager.repository_service.transition_repository_state.side_effect = _transition_repository_state
    mock_manager.repository_service.activate_repository.side_effect = lambda **kw: _transition_repository_state(
        state="active", **kw
    )
    mock_manager.repository_service.deactivate_repository.side_effect = lambda **kw: _transition_repository_state(
        state="inactive", **kw
    )
    mock_manager.repository_service.archive_repository.side_effect = lambda **kw: _transition_repository_state(
        state="archived", **kw
    )
    mock_manager.repository_service.rotate_credentials.side_effect = _rotate_credentials
    mock_manager.repository_service.rotate_repository_password.side_effect = _rotate_repository_password
    mock_manager.repository_service.rotate_repository_backend_credentials.side_effect = _rotate_backend_credentials
    mock_manager.repository_service.prune_repository.side_effect = _simple_success
    mock_manager.repository_service.migrate_repository.side_effect = _simple_success
    mock_manager.repository_service.forget_repository.side_effect = _simple_success
    mock_manager.repository_service.validate_repository.side_effect = lambda **_kw: {
        "status": "success",
        "errors": [],
        "warnings": [],
    }
    mock_manager.repository_service.batch_validate_repositories.side_effect = (
        lambda repositories=None, **_kw: [
            {
                "name": repo if isinstance(repo, str) else repo.get("name"),
                "status": "success",
            }
            for repo in (repositories or list(repo_store.values()))
        ]
    )

    # Snapshot service
    mock_manager.snapshot_service = Mock()
    mock_manager.snapshot_service.list_snapshots.return_value = snapshots or []
    mock_manager.snapshot_service.get_snapshot.return_value = None
    mock_manager.snapshot_service.find_snapshots.return_value = []
    mock_manager.snapshot_service.delete_snapshot.return_value = {'success': True}

    # Config module aligned with repo store
    config_module = MagicMock()
    config_module.get_repository.side_effect = lambda name: _ensure_repo(name)
    config_module.list_repositories.side_effect = lambda: list(repo_store.values())
    config_module.set_repository.side_effect = lambda repository, **_kw: repo_store.__setitem__(repository["name"], repository)
    config_module.remove_repository.side_effect = lambda name: repo_store.pop(name, None)
    config_module.set_default_repository.side_effect = _set_default_repository
    config_module.clear_default_repository.side_effect = _clear_default_repository
    mock_manager.config_module = config_module

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

    # Direct method access for CLI convenience
    mock_manager.list_repositories = mock_manager.repository_service.list_repositories
    mock_manager.get_repository = mock_manager.repository_service.get_repository
    mock_manager.add_repository = mock_manager.repository_service.add_repository
    mock_manager.remove_repository = mock_manager.repository_service.remove_repository
    mock_manager.update_repository = mock_manager.repository_service.update_repository
    mock_manager.update_repository_metadata = mock_manager.repository_service.update_repository_metadata
    mock_manager.update_repository_configuration = mock_manager.repository_service.update_repository_configuration
    mock_manager.initialize_repository = mock_manager.repository_service.initialize_repository
    mock_manager.check_repository = mock_manager.repository_service.check_repository
    mock_manager.get_repository_stats = mock_manager.repository_service.get_repository_stats
    mock_manager.list_snapshots = mock_manager.snapshot_service.list_snapshots
    mock_manager.get_snapshot = mock_manager.snapshot_service.get_snapshot
    mock_manager.find_snapshots = mock_manager.snapshot_service.find_snapshots
    mock_manager.rotate_credentials = mock_manager.repository_service.rotate_credentials
    mock_manager.rotate_repository_password = mock_manager.repository_service.rotate_repository_password
    mock_manager.rotate_repository_backend_credentials = (
        mock_manager.repository_service.rotate_repository_backend_credentials
    )

    # Persist stores for downstream consumers
    mock_manager._repo_store = repo_store
    mock_manager._ensure_repo = _ensure_repo
    mock_manager._default_state = default_state
    mock_manager._credential_store = credential_store

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
