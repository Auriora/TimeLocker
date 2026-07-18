"""
Shared fixtures for policy management tests.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock

from TimeLocker.policy.models import (
    BackupPolicy,
    RetentionPolicy,
    RetentionRule,
    PolicyAssignment,
    ScheduleConfig,
    ComplianceRule,
)
from TimeLocker.policy.types import (
    PolicyType,
    TargetType,
    RetentionType,
    PolicyStatus,
    ConflictResolution,
)
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.backup_repository import BackupRepository
from TimeLocker.selection_template_manager import SelectionTemplateManager
from TimeLocker.selection_models import SelectionTemplate, SelectionConfig


@pytest.fixture
def sample_retention_rule():
    """Create a sample retention rule."""
    return RetentionRule(
        type=RetentionType.DAILY,
        count=7,
        minimum_age=None,
        tag_filters=None,
    )


@pytest.fixture
def sample_retention_policy(sample_retention_rule):
    """Create a sample retention policy."""
    return RetentionPolicy(
        id="test-retention-policy",
        name="Test Retention Policy",
        description="Test retention policy for unit tests",
        rules=[sample_retention_rule],
        priority=0,
        status=PolicyStatus.ACTIVE,
    )


@pytest.fixture
def sample_backup_policy():
    """Create a sample backup policy."""
    return BackupPolicy(
        id="test-backup-policy",
        name="Test Backup Policy",
        description="Test backup policy for unit tests",
        data_selection_refs=["home-dir"],
        target_repositories=["local-repo"],
        backup_tool="restic",
        schedule=None,
        execution_params={},
        retention_policy_id="test-retention-policy",
        tags={"env": "test"},
        compliance_requirements=[],
        priority=0,
        status=PolicyStatus.ACTIVE,
    )


@pytest.fixture
def sample_policy_assignment():
    """Create a sample policy assignment."""
    return PolicyAssignment(
        id="test-assignment",
        policy_id="test-retention-policy",
        policy_type=PolicyType.RETENTION,
        target_type=TargetType.REPOSITORY,
        target_id="local-repo",
        priority=0,
        active=True,
        conflict_resolution=ConflictResolution.PRIORITY,
    )


@pytest.fixture
def mock_repository():
    """Create a mock backup repository."""
    repo = Mock(spec=BackupRepository)
    repo.name = "test-repo"
    repo.location = "/tmp/test-repo"
    repo.repository_type = "local"
    return repo


@pytest.fixture
def sample_snapshots():
    """Create sample backup snapshots for testing."""
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    snapshots = []
    
    # Create 10 daily snapshots
    for i in range(10):
        snapshot = Mock(spec=BackupSnapshot)
        snapshot.id = f"snapshot-{i:02d}"
        snapshot.timestamp = base_time - timedelta(days=i)
        snapshot.tags = {"type": "daily"}
        snapshot.size_bytes = 1000000 * (i + 1)
        snapshots.append(snapshot)
    
    return snapshots


@pytest.fixture
def mock_repository_manager():
    """Create a mock repository manager."""
    manager = Mock()
    manager.get_repository = Mock(return_value=None)
    manager.list_repositories = Mock(return_value=[])
    return manager


@pytest.fixture
def mock_config_manager():
    """Create a mock configuration manager."""
    manager = Mock()
    config = Mock()
    config.backup_targets = {"home-dir": {}}
    config.repositories = {"local-repo": {"uri": "/tmp/repo", "enabled": True}}
    manager.get_config = Mock(return_value=config)
    return manager


@pytest.fixture
def mock_policy_store():
    """Create a mock policy storage."""
    store = Mock()
    store.save_backup_policy = Mock()
    store.save_retention_policy = Mock()
    store.save_assignment = Mock()
    store.delete_backup_policy = Mock()
    store.delete_retention_policy = Mock()
    store.delete_assignment = Mock()
    store.list_backup_policies = Mock(return_value=[])
    store.list_retention_policies = Mock(return_value=[])
    store.list_assignments = Mock(return_value=[])
    store.list_enforcement_records = Mock(return_value=[])
    return store


@pytest.fixture(autouse=True)
def policy_selection_templates(tmp_path, monkeypatch):
    """
    Provide a default selection template for policy tests.
    
    Most tests rely on the legacy 'home-dir' reference, so we create a
    template with the same ID/name and patch the Policy modules to reuse
    this in-memory manager.
    """
    storage_dir = tmp_path / "policy-selection-templates"
    manager = SelectionTemplateManager(storage_dir=storage_dir)
    
    template = SelectionTemplate(
        id="home-dir",
        name="home-dir",
        description="Policy test template",
        selection_config=SelectionConfig(
            include_paths=[Path("/home/test")]
        )
    )
    manager.create_template(template)

    monkeypatch.setattr(
        "TimeLocker.policy.manager.SelectionTemplateManager",
        lambda *args, **kwargs: manager
    )
    monkeypatch.setattr(
        "TimeLocker.policy.validator.SelectionTemplateManager",
        lambda *args, **kwargs: manager
    )

    return manager
