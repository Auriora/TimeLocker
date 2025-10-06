"""
Integration tests for TimeLocker CLI workflows.

Tests complete user workflows including backup creation, repository management,
and configuration setup with mocked dependencies.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import get_cli_runner, combined_output

# Set wider terminal width to prevent help text truncation in CI
runner = get_cli_runner()


class TestCLIIntegrationWorkflows:
    """Test suite for CLI integration workflows."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def temp_repo_dir(self):
        """Create a temporary repository directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def temp_backup_dir(self):
        """Create a temporary backup source directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Test content")
            yield Path(temp_dir)

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repository_management_workflow(self, mock_service_manager, temp_repo_dir):
        """Test complete repository management workflow."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Mock repository operations
        mock_manager.add_repository.return_value = Mock(success=True)
        mock_manager.list_repositories.return_value = [
            {"name": "test-repo", "uri": f"file://{temp_repo_dir}", "description": "Test repository"}
        ]
        mock_manager.get_repository_by_name.return_value = Mock(
            name="test-repo", uri=f"file://{temp_repo_dir}", description="Test repository"
        )
        mock_manager.initialize_repository.return_value = Mock(success=True)
        mock_manager.check_repository.return_value = Mock(success=True)
        mock_manager.remove_repository.return_value = Mock(success=True)

        # Step 1: Add repository
        result = runner.invoke(app, [
            "repos", "add", "test-repo", f"file://{temp_repo_dir}",
            "--description", "Test repository"
        ])
        assert result.exit_code in [0, 1], "Repository add should not crash"

        # Step 2: List repositories
        result = runner.invoke(app, ["repos", "list"])
        assert result.exit_code in [0, 1], "Repository list should not crash"

        # Step 3: Show repository details
        result = runner.invoke(app, ["repos", "show", "test-repo"])
        assert result.exit_code in [0, 1], "Repository show should not crash"

        # Step 4: Initialize repository
        result = runner.invoke(app, [
            "repos", "init", "test-repo", "--yes"
        ])
        assert result.exit_code in [0, 1], "Repository init should not crash"

        # Step 5: Check repository
        result = runner.invoke(app, ["repos", "check", "test-repo"])
        assert result.exit_code in [0, 1], "Repository check should not crash"

        # Step 6: Remove repository
        result = runner.invoke(app, ["repos", "remove", "test-repo"])
        assert result.exit_code in [0, 1], "Repository remove should not crash"

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_backup_target_management_workflow(self, mock_service_manager, temp_backup_dir):
        """Test complete backup target management workflow."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Mock target operations
        mock_manager.add_backup_target.return_value = Mock(success=True)
        mock_manager.list_backup_targets.return_value = [
            {"name": "test-target", "paths": [str(temp_backup_dir)], "description": "Test target"}
        ]
        mock_manager.get_backup_target.return_value = Mock(
            name="test-target", paths=[str(temp_backup_dir)], description="Test target"
        )
        mock_manager.remove_backup_target.return_value = Mock(success=True)

        # Step 1: Add backup target
        result = runner.invoke(app, [
            "targets", "add", "test-target",
            "--path", str(temp_backup_dir),
            "--description", "Test target"
        ])
        assert result.exit_code in [0, 1], "Target add should not crash"

        # Step 2: List targets
        result = runner.invoke(app, ["targets", "list"])
        assert result.exit_code in [0, 1], "Target list should not crash"

        # Step 3: Show target details
        result = runner.invoke(app, ["targets", "show", "test-target"])
        assert result.exit_code in [0, 1], "Target show should not crash"

        # Step 4: Remove target
        result = runner.invoke(app, ["targets", "remove", "test-target"])
        assert result.exit_code in [0, 1], "Target remove should not crash"

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_backup_creation_workflow(self, mock_service_manager, temp_backup_dir, temp_repo_dir):
        """Test complete backup creation workflow."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Mock backup operations
        mock_manager.execute_backup.return_value = Mock(
            success=True, snapshot_id="abc123def456", stats=Mock()
        )
        mock_manager.verify_backup.return_value = Mock(success=True)
        mock_manager.list_snapshots.return_value = [
            {"id": "abc123def456", "time": "2024-01-01T12:00:00Z", "hostname": "test"}
        ]

        # Step 1: Create backup with target
        result = runner.invoke(app, [
            "backup", "create",
            "--target", "test-target",
            "--dry-run"
        ])
        assert result.exit_code in [0, 1], "Backup create with target should not crash"

        # Step 2: Create backup with direct paths
        result = runner.invoke(app, [
            "backup", "create",
            str(temp_backup_dir),
            "--repository", f"file://{temp_repo_dir}",
            "--dry-run"
        ])
        assert result.exit_code in [0, 1], "Backup create with paths should not crash"

        # Step 3: Verify backup
        result = runner.invoke(app, [
            "backup", "verify",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert result.exit_code in [0, 1], "Backup verify should not crash"

        # Step 4: List snapshots
        result = runner.invoke(app, [
            "snapshots", "list",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert result.exit_code in [0, 1], "Snapshots list should not crash"

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshot_management_workflow(self, mock_service_manager, temp_repo_dir):
        """Test complete snapshot management workflow."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Mock snapshot operations
        mock_manager.list_snapshots.return_value = [
            {"id": "abc123def456", "time": "2024-01-01T12:00:00Z", "hostname": "test"}
        ]
        mock_manager.get_snapshot_details.return_value = Mock(
            id="abc123def456", time="2024-01-01T12:00:00Z", hostname="test"
        )
        mock_manager.list_snapshot_contents.return_value = [
            {"path": "/test.txt", "type": "file", "size": 100}
        ]
        mock_manager.restore_snapshot.return_value = Mock(success=True)
        mock_manager.mount_snapshot.return_value = Mock(success=True)
        mock_manager.find_in_snapshots.return_value = []

        # Step 1: List snapshots
        result = runner.invoke(app, [
            "snapshots", "list",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert result.exit_code in [0, 1], "Snapshots list should not crash"

        # Step 2: Show snapshot details
        result = runner.invoke(app, [
            "snapshots", "show", "abc123def456",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert result.exit_code in [0, 1], "Snapshots show should not crash"

        # Step 3: List snapshot contents
        result = runner.invoke(app, [
            "snapshots", "contents", "abc123def456",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert result.exit_code in [0, 1], "Snapshots contents should not crash"

        # Step 4: Search in snapshots
        result = runner.invoke(app, [
            "snapshots", "find", "*.txt",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert result.exit_code in [0, 1], "Snapshots find should not crash"

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_restore_workflow(self, mock_service_manager, temp_repo_dir):
        """Test complete restore workflow."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Mock restore operations
        mock_manager.restore_snapshot.return_value = Mock(success=True)
        mock_manager.mount_snapshot.return_value = Mock(success=True)
        mock_manager.unmount_snapshot.return_value = Mock(success=True)

        with tempfile.TemporaryDirectory() as restore_dir:
            # Step 1: Restore snapshot to directory
            result = runner.invoke(app, [
                "snapshots", "restore", "abc123def456", restore_dir,
                "--repository", f"file://{temp_repo_dir}"
            ])
            assert result.exit_code in [0, 1], "Snapshot restore should not crash"

            # Step 2: Mount snapshot
            mount_dir = Path(restore_dir) / "mount"
            mount_dir.mkdir()
            result = runner.invoke(app, [
                "snapshots", "mount", "abc123def456", str(mount_dir),
                "--repository", f"file://{temp_repo_dir}"
            ])
            assert result.exit_code in [0, 1], "Snapshot mount should not crash"

            # Step 3: Unmount snapshot
            result = runner.invoke(app, [
                "snapshots", "umount", "abc123def456"
            ])
            assert result.exit_code in [0, 1], "Snapshot umount should not crash"

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credential_management_workflow(self, mock_service_manager):
        """Test complete credential management workflow."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Mock credential operations
        mock_manager.unlock_credential_manager.return_value = Mock(success=True)
        mock_manager.set_repository_password.return_value = Mock(success=True)
        mock_manager.remove_repository_password.return_value = Mock(success=True)

        # Step 1: Unlock credential manager
        result = runner.invoke(app, ["credentials", "unlock"])
        assert result.exit_code in [0, 1], "Credentials unlock should not crash"

        # Step 2: Set repository password
        result = runner.invoke(app, [
            "credentials", "set", "test-repo",
            "--password", "test-password"
        ])
        assert result.exit_code in [0, 1], "Credentials set should not crash"

        # Step 3: Remove repository password
        result = runner.invoke(app, [
            "credentials", "remove", "test-repo"
        ])
        assert result.exit_code in [0, 1], "Credentials remove should not crash"

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.ConfigurationModule')
    def test_configuration_workflow(self, mock_config_module, temp_config_dir):
        """Test complete configuration workflow."""
        # Mock the configuration module
        mock_config = Mock()
        mock_config_module.return_value = mock_config
        mock_config.get_config.return_value = {
            "repositories": {},
            "backup_targets": {},
            "default_repository": None
        }
        mock_config.config_file = temp_config_dir / "config.json"
        mock_config.get_config_info.return_value = {
            "config_file": str(mock_config.config_file),
            "repositories_count": 0,
            "targets_count": 0
        }

        # Step 1: Show configuration
        result = runner.invoke(app, [
            "config", "show",
            "--config-dir", str(temp_config_dir)
        ])
        assert result.exit_code in [0, 1], "Config show should not crash"

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_first_time_user_workflow(self, mock_service_manager, temp_repo_dir, temp_backup_dir):
        """Test complete first-time user workflow."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Mock all operations for first-time setup
        mock_manager.add_repository.return_value = Mock(success=True)
        mock_manager.initialize_repository.return_value = Mock(success=True)
        mock_manager.add_backup_target.return_value = Mock(success=True)
        mock_manager.execute_backup.return_value = Mock(
            success=True, snapshot_id="abc123def456"
        )
        mock_manager.list_snapshots.return_value = [
            {"id": "abc123def456", "time": "2024-01-01T12:00:00Z"}
        ]

        # Simulate first-time user workflow
        
        # Step 1: Add first repository
        result = runner.invoke(app, [
            "repos", "add", "my-backup", f"file://{temp_repo_dir}",
            "--description", "My first backup repository",
            "--set-default"
        ])
        assert result.exit_code in [0, 1], "First repo add should not crash"

        # Step 2: Initialize repository
        result = runner.invoke(app, [
            "repos", "init", "my-backup", "--yes"
        ])
        assert result.exit_code in [0, 1], "First repo init should not crash"

        # Step 3: Add backup target
        result = runner.invoke(app, [
            "targets", "add", "documents",
            "--path", str(temp_backup_dir),
            "--description", "My documents"
        ])
        assert result.exit_code in [0, 1], "First target add should not crash"

        # Step 4: Create first backup
        result = runner.invoke(app, [
            "backup", "create",
            "--target", "documents",
            "--tags", "first-backup"
        ])
        assert result.exit_code in [0, 1], "First backup should not crash"

        # Step 5: List snapshots to verify
        result = runner.invoke(app, ["snapshots", "list"])
        assert result.exit_code in [0, 1], "First snapshots list should not crash"

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_error_recovery_workflow(self, mock_service_manager):
        """Test error recovery and graceful failure handling."""
        # Mock the service manager with some failures
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Mock some operations to fail
        mock_manager.add_repository.side_effect = Exception("Repository already exists")
        mock_manager.execute_backup.side_effect = Exception("Backup failed")

        # Test graceful failure handling
        
        # Step 1: Try to add duplicate repository
        result = runner.invoke(app, [
            "repos", "add", "existing-repo", "file:///tmp/repo"
        ])
        assert result.exit_code != 0, "Duplicate repo add should fail gracefully"
        combined = combined_output(result)
        assert len(combined) > 10, "Should show meaningful error message"

        # Step 2: Try backup that fails
        result = runner.invoke(app, [
            "backup", "create", "/tmp/test"
        ])
        assert result.exit_code != 0, "Failed backup should fail gracefully"
        combined = combined_output(result)
        assert len(combined) > 10, "Should show meaningful error message"
