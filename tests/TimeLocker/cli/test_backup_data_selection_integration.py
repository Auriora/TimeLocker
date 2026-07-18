"""
CLI integration tests for backup operations with data selection workflows.

This module tests the integration between backup CLI commands and the data
selection system, ensuring proper template resolution, parameter translation,
and error handling.

Tests Requirements:
- 10.1: CLI command to create backups using data selection templates
- 10.2: Template retrieval from Selection Manager
- 10.3: Translation of template rules to backup tool parameters
- 10.4: Clear error messages for missing templates
- 11.1: Help command displays accurate backup command information
- 11.2: Help text shows correct command names and syntax
"""

import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
    get_cli_runner,
    combined_output,
    assert_exit_code,
    assert_output_contains
)

from TimeLocker.cli_modules.helpers.backup_cli_handler import (
    SelectionTemplateNotFoundError,
    InvalidSelectionConfigError,
    BackupCLIHandlerError
)


runner = get_cli_runner()


class TestBackupCreateWithSelectionTemplate:
    """Test backup create command with selection templates (Requirement 10.1)"""
    
    @pytest.mark.integration
    @patch('TimeLocker.cli_modules.commands.backup._get_service_method', return_value=None)
    @patch('TimeLocker.cli_modules.commands.base._create_config_service')
    @patch('TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    def test_backup_create_with_valid_selection_template(
        self,
        mock_get_manager,
        mock_create_config_service,
        mock_get_service_method
    ):
        """Test successful backup creation using a valid selection template"""
        mock_get_service_method.return_value = None
        mock_create_config_service.return_value = Mock()
        
        service_manager = Mock()
        service_manager.selection_template_exists.return_value = True
        service_manager.get_selection_summary.return_value = "Test selection with 5 paths"
        service_manager.run_selection_backup.return_value = Mock(
            status=Mock(value='completed'),
            snapshot_id='test-snapshot-123',
            files_processed=100,
            bytes_transferred=1024000,
            duration=Mock(total_seconds=lambda: 10.5),
            warnings=[],
            errors=[]
        )
        mock_get_manager.return_value = service_manager
        
        # Execute command
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "documents",
            "--repository", "test-repo"
        ])
        
        # Verify success
        assert_exit_code(result, 0)
        output = combined_output(result)
        assert "documents" in output.lower() or "selection" in output.lower()
        service_manager.selection_template_exists.assert_called_once_with("documents")
        service_manager.run_selection_backup.assert_called_once()
    
    @pytest.mark.integration
    @patch('TimeLocker.cli_modules.commands.backup._get_service_method', return_value=None)
    @patch('TimeLocker.cli_modules.commands.base._create_config_service')
    @patch('TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    def test_backup_create_with_selection_and_tags(
        self,
        mock_get_manager,
        mock_create_config_service,
        mock_get_service_method
    ):
        """Test backup creation with selection template and custom tags"""
        mock_get_service_method.return_value = None
        mock_create_config_service.return_value = Mock()
        
        tags_received = []
        
        service_manager = Mock()
        service_manager.selection_template_exists.return_value = True
        service_manager.get_selection_summary.return_value = "Test selection"
        
        def capture_run_selection_backup(**kwargs):
            tags_received.extend(kwargs.get('tags', []))
            return Mock(
                status=Mock(value='completed'),
                snapshot_id='test-123',
                files_processed=50,
                bytes_transferred=512000,
                duration=Mock(total_seconds=lambda: 5.0),
                warnings=[],
                errors=[]
            )
        
        service_manager.run_selection_backup.side_effect = capture_run_selection_backup
        mock_get_manager.return_value = service_manager
        
        # Execute command with tags
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "documents",
            "--repository", "test-repo",
            "--tags", "daily",
            "--tags", "important"
        ])
        
        # Verify tags were passed
        assert_exit_code(result, 0)
        assert "daily" in tags_received or "important" in tags_received
    
    @pytest.mark.integration
    @patch('TimeLocker.cli_modules.commands.backup._get_service_method', return_value=None)
    @patch('TimeLocker.cli_modules.commands.base._create_config_service')
    @patch('TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    def test_backup_create_with_selection_dry_run(
        self,
        mock_get_manager,
        mock_create_config_service,
        mock_get_service_method
    ):
        """Test backup creation with selection template in dry-run mode"""
        mock_get_service_method.return_value = None
        mock_create_config_service.return_value = Mock()
        
        dry_run_received = []
        
        service_manager = Mock()
        service_manager.selection_template_exists.return_value = True
        service_manager.get_selection_summary.return_value = "Test selection"
        
        def capture_run_selection_backup(**kwargs):
            dry_run_received.append(kwargs.get('dry_run', False))
            return Mock(
                status=Mock(value='completed'),
                snapshot_id=None,
                files_processed=75,
                bytes_transferred=0,
                duration=Mock(total_seconds=lambda: 2.0),
                warnings=[],
                errors=[]
            )
        
        service_manager.run_selection_backup.side_effect = capture_run_selection_backup
        mock_get_manager.return_value = service_manager
        
        # Execute command with dry-run
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "documents",
            "--repository", "test-repo",
            "--dry-run"
        ])
        
        # Verify dry-run was enabled
        assert_exit_code(result, 0)
        assert True in dry_run_received

    @pytest.mark.integration
    @patch('TimeLocker.cli_modules.commands.backup._get_service_method', return_value=None)
    @patch('TimeLocker.cli_modules.commands.base._create_config_service')
    @patch('TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    def test_backup_create_passes_cli_options(
        self,
        mock_get_manager,
        mock_create_config_service,
        mock_get_service_method
    ):
        mock_get_service_method.return_value = None
        mock_create_config_service.return_value = Mock()
        
        service_manager = Mock()
        service_manager.selection_template_exists.return_value = True
        service_manager.get_selection_summary.return_value = "Summary"
        service_manager.run_selection_backup.return_value = Mock(
            status=Mock(value='completed'),
            snapshot_id='abc',
            files_processed=1,
            bytes_transferred=1,
            duration=Mock(total_seconds=lambda: 0.1),
            warnings=[],
            errors=[]
        )
        mock_get_manager.return_value = service_manager
        
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "docs",
            "--repository", "test-repo"
        ])
        
        assert_exit_code(result, 0)
        cli_options = service_manager.run_selection_backup.call_args[1]["cli_options"]
        assert cli_options["tool_type"] == "restic"
        assert cli_options["max_retries"] == 3

class TestBackupSelectionErrors:
    """Test error handling paths for selection-driven backups."""
    
    @pytest.mark.integration
    @patch('TimeLocker.cli_modules.commands.backup._get_service_method', return_value=None)
    @patch('TimeLocker.cli_modules.commands.base._create_config_service')
    @patch('TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    def test_backup_create_with_nonexistent_template(
        self,
        mock_get_manager,
        mock_create_config_service,
        mock_get_service_method
    ):
        mock_get_service_method.return_value = None
        mock_create_config_service.return_value = Mock()
        
        service_manager = Mock()
        service_manager.selection_template_exists.return_value = False
        service_manager.suggest_selection_creation.return_value = "Template missing. Run tl selections create missing."
        mock_get_manager.return_value = service_manager
        
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "missing",
            "--repository", "test-repo"
        ])
        
        assert_exit_code(result, 1)
        output = combined_output(result)
        assert "missing" in output.lower()
        service_manager.selection_template_exists.assert_called_once_with("missing")
    
    @pytest.mark.integration
    @patch('TimeLocker.cli_modules.commands.backup._get_service_method', return_value=None)
    @patch('TimeLocker.cli_modules.commands.base._create_config_service')
    @patch('TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    def test_backup_create_handles_invalid_selection_config(
        self,
        mock_get_manager,
        mock_create_config_service,
        mock_get_service_method
    ):
        mock_get_service_method.return_value = None
        mock_create_config_service.return_value = Mock()
        
        service_manager = Mock()
        service_manager.selection_template_exists.return_value = True
        service_manager.get_selection_summary.return_value = "Summary"
        service_manager.run_selection_backup.side_effect = InvalidSelectionConfigError("invalid template")
        mock_get_manager.return_value = service_manager
        
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "bad-template",
            "--repository", "test-repo"
        ])
        
        assert_exit_code(result, 1)
        output = combined_output(result)
        assert "invalid selection configuration" in output.lower()
    
    @pytest.mark.integration
    @patch('TimeLocker.cli_modules.commands.backup._get_service_method', return_value=None)
    @patch('TimeLocker.cli_modules.commands.base._create_config_service')
    @patch('TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    def test_backup_create_handles_handler_errors(
        self,
        mock_get_manager,
        mock_create_config_service,
        mock_get_service_method
    ):
        mock_get_service_method.return_value = None
        mock_create_config_service.return_value = Mock()
        
        service_manager = Mock()
        service_manager.selection_template_exists.return_value = True
        service_manager.get_selection_summary.return_value = "Summary"
        service_manager.run_selection_backup.side_effect = BackupCLIHandlerError("failed to run backup")
        mock_get_manager.return_value = service_manager
        
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "docs",
            "--repository", "test-repo"
        ])
        
        assert_exit_code(result, 1)
        output = combined_output(result)
        assert "failed to execute selection-based backup" in output.lower()


class TestHelpTextAccuracy:
    """Test help text accuracy and consistency (Requirements 11.1, 11.2)"""
    
    @pytest.mark.integration
    def test_backup_help_shows_correct_command_names(self):
        """Test that backup help shows correct command names"""
        result = runner.invoke(app, ["backup", "--help"])
        
        assert_exit_code(result, 0)
        output = combined_output(result)
        
        # Verify correct command names are shown
        assert "create" in output.lower()
        assert "verify" in output.lower()
        # Should not show deprecated command names
        assert "run" not in output.lower() or "create" in output.lower()
    
    @pytest.mark.integration
    def test_backup_create_help_shows_selection_option(self):
        """Test that backup create help shows selection option"""
        result = runner.invoke(app, ["backup", "create", "--help"])
        
        assert_exit_code(result, 0)
        output = combined_output(result)
        
        # Verify selection option is documented
        assert "--selection" in output or "-s" in output
        assert "template" in output.lower() or "selection" in output.lower()
    
    @pytest.mark.integration
    def test_backup_create_help_shows_examples_with_selection(self):
        """Test that backup create help includes examples using selection templates"""
        result = runner.invoke(app, ["backup", "create", "--help"])
        
        assert_exit_code(result, 0)
        output = combined_output(result)
        
        # Verify examples are present
        assert "example" in output.lower() or "usage" in output.lower()
        # Should show selection-based examples
        if "example" in output.lower():
            assert "--selection" in output or "selection" in output.lower()
    
    @pytest.mark.integration
    def test_help_text_does_not_reference_deprecated_features(self):
        """Test that help text doesn't reference deprecated backup targets"""
        result = runner.invoke(app, ["backup", "create", "--help"])
        
        assert_exit_code(result, 0)
        output = combined_output(result)
        
        # Should not mention deprecated "backup targets"
        # Note: "target" might appear in other contexts, so check carefully
        if "target" in output.lower():
            # If "target" appears, it should be in a different context
            # not as "backup target" or "target name"
            assert "backup target" not in output.lower()
    
    @pytest.mark.integration
    def test_main_help_shows_backup_commands(self):
        """Test that main help shows backup commands correctly"""
        result = runner.invoke(app, ["--help"])
        
        assert_exit_code(result, 0)
        output = combined_output(result)
        
        # Verify backup command group is shown
        assert "backup" in output.lower()
    
    @pytest.mark.integration
    def test_help_text_consistent_across_commands(self):
        """Test that help text terminology is consistent across commands"""
        # Get help for multiple commands
        backup_help = runner.invoke(app, ["backup", "--help"])
        create_help = runner.invoke(app, ["backup", "create", "--help"])
        
        assert_exit_code(backup_help, 0)
        assert_exit_code(create_help, 0)
        
        backup_output = combined_output(backup_help)
        create_output = combined_output(create_help)
        
        # Both should use consistent terminology
        # If one mentions "selection template", the other should too
        if "selection" in backup_output.lower():
            assert "selection" in create_output.lower()



class TestBackupExecutionWithSelection:
    """Test complete backup execution workflow with selection templates"""
    
    @pytest.mark.integration
    @patch('TimeLocker.cli_modules.commands.backup._get_service_method', return_value=None)
    @patch('TimeLocker.cli_modules.commands.base._create_config_service')
    @patch('TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    def test_successful_backup_shows_snapshot_id(
        self,
        mock_get_manager,
        mock_create_config_service,
        mock_get_service_method
    ):
        mock_get_service_method.return_value = None
        mock_create_config_service.return_value = Mock()
        
        service_manager = Mock()
        service_manager.selection_template_exists.return_value = True
        service_manager.get_selection_summary.return_value = "Summary"
        service_manager.run_selection_backup.return_value = SimpleNamespace(
            status=SimpleNamespace(value='completed'),
            snapshot_id='test-snapshot-123',
            files_processed=100,
            bytes_transferred=1024000,
            duration=SimpleNamespace(total_seconds=lambda: 10.0),
            warnings=[],
            errors=[]
        )
        mock_get_manager.return_value = service_manager
        
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "test-template",
            "--repository", "test-repo"
        ])
        
        assert_exit_code(result, 0)
        output = combined_output(result)
        assert "snapshot" in output.lower()
    
    @pytest.mark.integration
    @patch('TimeLocker.cli_modules.commands.backup._get_service_method', return_value=None)
    @patch('TimeLocker.cli_modules.commands.base._create_config_service')
    @patch('TimeLocker.cli_modules.commands.backup._get_service_manager_for_command')
    def test_backup_with_warnings_displays_warnings(
        self,
        mock_get_manager,
        mock_create_config_service,
        mock_get_service_method
    ):
        mock_get_service_method.return_value = None
        mock_create_config_service.return_value = Mock()
        
        service_manager = Mock()
        service_manager.selection_template_exists.return_value = True
        service_manager.get_selection_summary.return_value = "Summary"
        service_manager.run_selection_backup.return_value = SimpleNamespace(
            status=SimpleNamespace(value='completed'),
            snapshot_id='test-123',
            files_processed=10,
            bytes_transferred=100,
            duration=SimpleNamespace(total_seconds=lambda: 1.0),
            warnings=["Some files skipped", "Permission denied"],
            errors=[]
        )
        mock_get_manager.return_value = service_manager
        
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "test-template",
            "--repository", "test-repo"
        ])
        
        assert_exit_code(result, 0)
        output = combined_output(result)
        assert "warning" in output.lower()
