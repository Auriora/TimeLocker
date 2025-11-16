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
from tests.TimeLocker.cli.test_utils import (
        get_cli_runner,
        combined_output,
        assert_success,
        create_mock_service_manager,
        patch_restore_commands,
)

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
    @patch('src.TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repository_management_workflow(self, mock_get_service_manager, mock_get_for_command, temp_repo_dir):
        """Test complete repository management workflow."""
        # Mock the service manager with proper structure
        mock_manager = create_mock_service_manager()
        mock_get_service_manager.return_value = mock_manager
        mock_get_for_command.return_value = mock_manager
        
        # Mock repository operations with proper return values
        mock_manager.add_repository.return_value = {"success": True}
        mock_manager.repository_service.add_repository.return_value = {"success": True}
        mock_manager.list_repositories.return_value = [
            {"name": "test-repo", "uri": f"file://{temp_repo_dir}", "description": "Test repository"}
        ]
        mock_manager.repository_service.list_repositories.return_value = [
            {"name": "test-repo", "uri": f"file://{temp_repo_dir}", "description": "Test repository"}
        ]
        mock_manager.get_repository_by_name.return_value = Mock(
            name="test-repo", uri=f"file://{temp_repo_dir}", description="Test repository"
        )
        mock_manager.repository_service.get_repository.return_value = Mock(
            name="test-repo", uri=f"file://{temp_repo_dir}", description="Test repository"
        )
        mock_manager.config_module.get_repository.return_value = Mock(
            name="test-repo", location=f"file://{temp_repo_dir}", description="Test repository"
        )
        mock_manager.initialize_repository.return_value = {"success": True, "already_initialized": False}
        mock_manager.repository_service.initialize_repository.return_value = {"success": True, "already_initialized": False}
        mock_manager.check_repository.return_value = {"success": True}
        mock_manager.repository_service.check_repository.return_value = {"success": True}
        mock_manager.remove_repository.return_value = {"success": True}
        mock_manager.repository_service.remove_repository.return_value = {"success": True}

        # Step 1: Add repository
        result = runner.invoke(app, [
            "repos", "add", "test-repo", f"file://{temp_repo_dir}",
            "--description", "Test repository"
        ])
        assert_success(result, "Repository add should succeed with mocked service manager")

        # Step 2: List repositories
        result = runner.invoke(app, ["repos", "list"])
        assert_success(result, "Repository list should succeed with mocked service manager")

        # Step 3: Show repository details
        result = runner.invoke(app, ["repos", "show", "test-repo"])
        assert_success(result, "Repository show should succeed with mocked service manager")

        # Step 4: Initialize repository
        result = runner.invoke(app, [
            "repos", "init", "test-repo", "--yes", "--password", "test-pass",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert_success(result, "Repository init should succeed with mocked service manager")

        # Step 5: Check repository
        result = runner.invoke(app, ["repos", "check", "test-repo"])
        assert_success(result, "Repository check should succeed with mocked service manager")

        # Step 6: Remove repository (with --yes flag for non-interactive mode)
        result = runner.invoke(app, ["repos", "remove", "test-repo", "--yes"])
        assert_success(result, "Repository remove should succeed with mocked service manager")

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('src.TimeLocker.cli_modules.commands.backup.get_cli_service_manager')
    @patch('src.TimeLocker.cli._get_service_manager_for_command')
    def test_backup_creation_workflow(self, mock_get_for_command, mock_backup_get_service_manager, mock_cli_services_get, temp_backup_dir, temp_repo_dir):
        """Test complete backup creation workflow."""
        # Mock the service manager
        mock_manager = create_mock_service_manager()
        mock_backup_get_service_manager.return_value = mock_manager
        mock_cli_services_get.return_value = mock_manager
        mock_get_for_command.return_value = mock_manager
        
        # Mock backup operations
        mock_manager.execute_backup.return_value = Mock(
            success=True, snapshot_id="abc123def456", warnings=[], errors=[]
        )
        mock_manager.verify_backup_integrity.return_value = True
        mock_manager.snapshot_service.list_snapshots.return_value = [
            {"id": "abc123def456", "time": "2024-01-01T12:00:00Z", "hostname": "test"}
        ]

        # Step 1: Create backup with direct paths
        result = runner.invoke(app, [
            "backup", "create",
            str(temp_backup_dir),
            "--repository", f"file://{temp_repo_dir}",
            "--dry-run"
        ])
        assert_success(result, "Backup create with paths should succeed with mocked service manager")

        # Step 2: Verify backup
        result = runner.invoke(app, [
            "backup", "verify",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert_success(result, "Backup verify should succeed with mocked service manager")

        # Step 3: List snapshots
        result = runner.invoke(app, [
            "snapshots", "list",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert_success(result, "Snapshots list should succeed with mocked service manager")

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshot_management_workflow(self, mock_service_manager, temp_repo_dir):
        """Test complete snapshot management workflow."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Mock snapshot service operations
        snapshot_service = Mock()
        mock_manager.snapshot_service = snapshot_service
        snapshot_service.list_snapshots.return_value = [
            {"id": "abc123def456", "time": "2024-01-01T12:00:00Z", "hostname": "test"}
        ]
        snapshot_service.get_snapshot_details = Mock(return_value=Mock(
            id="abc123def456", time="2024-01-01T12:00:00Z", hostname="test"
        ))

        # Step 1: List snapshots
        result = runner.invoke(app, [
            "snapshots", "list",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert_success(result, "Snapshots list should succeed with mocked service manager")

        # Step 2: Show snapshot details
        result = runner.invoke(app, [
            "snapshots", "show", "abc123def456",
            "--repository", f"file://{temp_repo_dir}"
        ])
        assert_success(result, "Snapshots show should succeed with mocked service manager")

        with patch_restore_commands(mode="success"):
            # Step 3: Browse snapshot contents through restore namespace
            result = runner.invoke(app, [
                "restore", "browse",
                f"file://{temp_repo_dir}",
                "abc123def456"
            ])
            assert_success(result, "Restore browse should succeed with mocked dependencies")

            # Step 4: Search snapshot files via restore namespace
            result = runner.invoke(app, [
                "restore", "find",
                f"file://{temp_repo_dir}",
                "*.txt",
                "--snapshot", "abc123def456"
            ])
            assert_success(result, "Restore find should succeed with mocked dependencies")

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

        with patch_restore_commands(mode="success"):
            with tempfile.TemporaryDirectory() as restore_dir:
                # Step 1: Restore snapshot to directory using restore namespace
                result = runner.invoke(app, [
                    "restore", "full",
                    f"file://{temp_repo_dir}",
                    "abc123def456",
                    restore_dir
                ])
                assert_success(result, "Restore full should succeed with mocked dependencies")

                # Step 2: Mount snapshot
                mount_dir = Path(restore_dir) / "mount"
                mount_dir.mkdir()
                result = runner.invoke(app, [
                    "restore", "mount",
                    f"file://{temp_repo_dir}",
                    "abc123def456",
                    str(mount_dir)
                ])
                assert_success(result, "Restore mount should succeed with mocked dependencies")

                # Step 3: Unmount snapshot (currently not implemented)
                result = runner.invoke(app, [
                    "restore", "umount", "abc123def456"
                ])
                combined = combined_output(result)
                assert result.exit_code != 0, "Restore umount should report not implemented"
                assert "not implemented" in combined.lower()

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
        result = runner.invoke(app, ["credentials", "unlock", "--password", "test-master"])
        assert_success(result, "Credentials unlock should succeed with mocked service manager")

        # Step 2: Set repository password
        result = runner.invoke(app, [
            "credentials", "set", "test-repo",
            "--password", "test-password",
            "--master-password", "test-master"
        ])
        assert_success(result, "Credentials set should succeed with mocked service manager")

        # Step 3: Remove repository password
        result = runner.invoke(app, [
            "credentials", "remove", "test-repo",
            "--password", "test-master"
        ])
        assert_success(result, "Credentials remove should succeed with mocked service manager")

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
        assert_success(result, "Config show should succeed with mocked configuration")

    @pytest.mark.integration
    @patch('src.TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    @patch('src.TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_first_time_user_workflow(
            self,
            mock_cli_service_manager,
            mock_repos_service_manager,
            mock_backup_service_manager,
            temp_repo_dir,
            temp_backup_dir,
            temp_config_dir,
            monkeypatch
    ):
        """Test complete first-time user workflow using selections."""
        # Isolate configuration and selection storage paths
        config_home = temp_config_dir / "config"
        data_home = temp_config_dir / "data"
        config_home.mkdir(parents=True, exist_ok=True)
        data_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("TIMELOCKER_TEST_MODE", "1")
        monkeypatch.setenv("TIMELOCKER_CONFIG_DIR", str(config_home))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))

        # Standardized mock service manager
        mock_manager = create_mock_service_manager()
        mock_cli_service_manager.return_value = mock_manager
        mock_repos_service_manager.return_value = mock_manager
        mock_backup_service_manager.return_value = mock_manager

        # Provide backup orchestrator capable of execute_backup_job
        orchestrator = Mock()
        backup_result = Mock()
        backup_result.status = Mock()
        backup_result.status.value = "completed"
        backup_result.snapshot_id = "abc123def456"
        backup_result.files_processed = 42
        backup_result.bytes_transferred = 1024
        backup_result.duration = Mock()
        backup_result.duration.total_seconds.return_value = 12.5
        backup_result.warnings = []
        backup_result.errors = []
        orchestrator.execute_backup_job.return_value = backup_result
        mock_manager._backup_orchestrator = orchestrator
        mock_manager.backup_orchestrator = orchestrator

        # Snapshot listing expectations
        snapshot_entry = {"id": "abc123def456", "time": "2024-01-01T12:00:00Z"}
        mock_manager.snapshot_service.list_snapshots.return_value = [snapshot_entry]
        mock_manager.list_snapshots.return_value = [snapshot_entry]

        # Step 1: Add first repository and set default
        result = runner.invoke(app, [
            "repos", "add", "my-backup", f"file://{temp_repo_dir}",
            "--description", "My first backup repository",
            "--set-default"
        ])
        assert_success(result, "First repo add should succeed with mocked service manager")

        # Step 2: Initialize repository
        result = runner.invoke(app, [
            "repos", "init", "my-backup", "--yes",
            "--password", "test-repo-pass"
        ])
        assert_success(result, "Repository init should succeed with mocked service manager")

        # Step 3: Create an initial data selection template
        selection_name = "quick-start-docs"
        result = runner.invoke(app, [
            "selections", "create", selection_name,
            "--description", "Initial documents selection",
            "--include-path", str(temp_backup_dir)
        ])
        assert_success(result, "Selection creation should succeed")

        # Step 4: List selections to confirm discoverability
        result = runner.invoke(app, ["selections", "list"])
        assert_success(result, "Selection listing should succeed")

        # Step 5: Run first backup using the selection template
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", selection_name,
            "--repository", "my-backup",
            "--dry-run"
        ])
        assert_success(result, "Backup create should succeed with mocked orchestrator")
        combined = combined_output(result)
        assert selection_name in combined

        mock_manager.run_selection_backup.assert_called_once()
        run_kwargs = mock_manager.run_selection_backup.call_args.kwargs
        assert run_kwargs["selection_name"] == selection_name
        assert run_kwargs["repository"] == "my-backup"

        # Step 6: List snapshots to verify workflow summary
        result = runner.invoke(app, ["snapshots", "list"])
        assert_success(result, "Snapshots list should succeed with mocked service manager")

    @pytest.mark.integration
    @patch('src.TimeLocker.cli_modules.commands.backup.get_cli_service_manager')
    @patch('src.TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_error_recovery_workflow(self, mock_get_for_command, mock_service_manager):
        """Test error recovery and graceful failure handling."""
        # Mock the service manager with some failures
        mock_manager = create_mock_service_manager()
        mock_service_manager.return_value = mock_manager
        mock_get_for_command.return_value = mock_manager
        
        # Mock some operations to fail
        mock_manager.add_repository.side_effect = Exception("Repository already exists")
        mock_manager.repository_service.add_repository.side_effect = Exception("Repository already exists")
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
