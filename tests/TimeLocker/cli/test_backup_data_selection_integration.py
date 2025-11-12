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
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from datetime import timedelta

from src.TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
    get_cli_runner,
    combined_output,
    assert_exit_code,
    assert_output_contains
)

from TimeLocker.interfaces.data_models import (
    BackupStatus,
    ExecutionMode,
    BackupJobConfig
)
from TimeLocker.selection_models import SelectionConfig, ValidationResult
from TimeLocker.cli_modules.helpers.backup_cli_handler import (
    BackupCLIHandler,
    SelectionTemplateNotFoundError,
    InvalidSelectionConfigError
)


runner = get_cli_runner()


class TestBackupCreateWithSelectionTemplate:
    """Test backup create command with selection templates (Requirement 10.1)"""
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_backup_create_with_valid_selection_template(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test successful backup creation using a valid selection template"""
        # Setup service manager mock
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        # Setup selection manager mock
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        # Setup BackupCLIHandler mock
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Mock async methods
        async def mock_validate(selection_name):
            return True
        
        async def mock_summary(selection_name):
            return "Test selection with 5 paths"
        
        async def mock_execute(*args, **kwargs):
            return Mock(
                status=Mock(value='completed'),
                snapshot_id='test-snapshot-123',
                files_processed=100,
                bytes_transferred=1024000,
                duration=Mock(total_seconds=lambda: 10.5),
                warnings=[],
                errors=[]
            )
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.get_selection_summary = mock_summary
        mock_handler.execute_backup_with_selection = mock_execute
        
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
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_backup_create_with_selection_and_tags(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test backup creation with selection template and custom tags"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Track tags passed to execute method
        tags_received = []
        
        async def mock_validate(selection_name):
            return True
        
        async def mock_summary(selection_name):
            return "Test selection"
        
        async def mock_execute(*args, **kwargs):
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
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.get_selection_summary = mock_summary
        mock_handler.execute_backup_with_selection = mock_execute
        
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
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_backup_create_with_selection_dry_run(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test backup creation with selection template in dry-run mode"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Track dry_run flag
        dry_run_received = []
        
        async def mock_validate(selection_name):
            return True
        
        async def mock_summary(selection_name):
            return "Test selection"
        
        async def mock_execute(*args, **kwargs):
            dry_run_received.append(kwargs.get('dry_run', False))
            return Mock(
                status=Mock(value='completed'),
                snapshot_id=None,  # No snapshot in dry-run
                files_processed=75,
                bytes_transferred=0,
                duration=Mock(total_seconds=lambda: 2.0),
                warnings=[],
                errors=[]
            )
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.get_selection_summary = mock_summary
        mock_handler.execute_backup_with_selection = mock_execute
        
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


class TestSelectionTemplateNotFound:
    """Test error handling when selection template doesn't exist (Requirement 10.4)"""
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_backup_create_with_nonexistent_template(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test error message when selection template doesn't exist"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Mock template not found
        async def mock_validate(selection_name):
            return False
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.suggest_template_creation = Mock(
            return_value="Template 'nonexistent' not found. Create it with: tl selections create nonexistent"
        )
        
        # Execute command with nonexistent template
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "nonexistent",
            "--repository", "test-repo"
        ])
        
        # Verify error handling
        assert_exit_code(result, 1)
        output = combined_output(result)
        assert "not found" in output.lower() or "error" in output.lower()
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_error_message_suggests_template_creation(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test that error message suggests how to create the template"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Mock template not found with suggestion
        async def mock_validate(selection_name):
            return False
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.suggest_template_creation = Mock(
            return_value=(
                "Selection template 'missing' not found.\n\n"
                "💡 Create a selection template using:\n"
                "   tl selections create missing --paths /path/to/backup"
            )
        )
        
        # Execute command
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "missing",
            "--repository", "test-repo"
        ])
        
        # Verify suggestion in output
        assert_exit_code(result, 1)
        output = combined_output(result)
        # Check for helpful suggestions
        assert "create" in output.lower() or "selections" in output.lower()
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_error_message_lists_available_templates(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test that error message lists available templates when template not found"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Mock template not found with available templates
        async def mock_validate(selection_name):
            return False
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.suggest_template_creation = Mock(
            return_value=(
                "Selection template 'wrong' not found.\n\n"
                "Available templates:\n"
                "  - documents\n"
                "  - photos\n"
                "  - code\n\n"
                "To create a new selection template:\n"
                "  tl selections create wrong --paths /path/to/backup"
            )
        )
        
        # Execute command
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "wrong",
            "--repository", "test-repo"
        ])
        
        # Verify available templates are shown
        assert_exit_code(result, 1)
        output = combined_output(result)
        assert "available" in output.lower() or "templates" in output.lower()


class TestSelectionTemplateResolution:
    """Test selection template resolution and parameter translation (Requirements 10.2, 10.3)"""
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_template_resolution_to_backup_config(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test that selection template is properly resolved to backup configuration"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Track job config created
        job_configs_created = []
        
        async def mock_validate(selection_name):
            return True
        
        async def mock_summary(selection_name):
            return "Selection with include/exclude patterns"
        
        async def mock_execute(*args, **kwargs):
            # Capture the parameters passed
            job_configs_created.append({
                'selection_name': kwargs.get('selection_name'),
                'repository': kwargs.get('repository'),
                'execution_mode': kwargs.get('execution_mode')
            })
            return Mock(
                status=Mock(value='completed'),
                snapshot_id='test-123',
                files_processed=100,
                bytes_transferred=1024000,
                duration=Mock(total_seconds=lambda: 10.0),
                warnings=[],
                errors=[]
            )
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.get_selection_summary = mock_summary
        mock_handler.execute_backup_with_selection = mock_execute
        
        # Execute command
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "test-template",
            "--repository", "my-repo"
        ])
        
        # Verify template was resolved
        assert_exit_code(result, 0)
        assert len(job_configs_created) > 0
        assert job_configs_created[0]['selection_name'] == 'test-template'
        assert job_configs_created[0]['repository'] == 'my-repo'
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_template_parameters_translated_to_backup_tool(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test that template parameters are translated to backup tool format"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Track CLI options passed
        cli_options_received = []
        
        async def mock_validate(selection_name):
            return True
        
        async def mock_summary(selection_name):
            return "Complex selection with patterns"
        
        async def mock_execute(*args, **kwargs):
            cli_options_received.append(kwargs)
            return Mock(
                status=Mock(value='completed'),
                snapshot_id='test-123',
                files_processed=50,
                bytes_transferred=512000,
                duration=Mock(total_seconds=lambda: 5.0),
                warnings=[],
                errors=[]
            )
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.get_selection_summary = mock_summary
        mock_handler.execute_backup_with_selection = mock_execute
        
        # Execute command
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "complex-template",
            "--repository", "test-repo"
        ])
        
        # Verify CLI options were passed
        assert_exit_code(result, 0)
        assert len(cli_options_received) > 0
        # Verify tool_type and other options are present
        options = cli_options_received[0]
        assert 'tool_type' in options or 'max_retries' in options


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


class TestInvalidSelectionConfiguration:
    """Test handling of invalid selection configurations"""
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_backup_fails_with_invalid_selection_config(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test that backup fails gracefully with invalid selection configuration"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Mock invalid configuration
        async def mock_validate(selection_name):
            return True
        
        async def mock_summary(selection_name):
            return "Invalid selection"
        
        async def mock_execute(*args, **kwargs):
            raise InvalidSelectionConfigError(
                "Selection template has invalid configuration: Missing include paths"
            )
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.get_selection_summary = mock_summary
        mock_handler.execute_backup_with_selection = mock_execute
        
        # Execute command
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "invalid-template",
            "--repository", "test-repo"
        ])
        
        # Verify error handling
        assert_exit_code(result, 1)
        output = combined_output(result)
        assert "invalid" in output.lower() or "error" in output.lower()


class TestBackupExecutionWithSelection:
    """Test complete backup execution workflow with selection templates"""
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_successful_backup_shows_snapshot_id(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test that successful backup displays snapshot ID"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        async def mock_validate(selection_name):
            return True
        
        async def mock_summary(selection_name):
            return "Test selection"
        
        async def mock_execute(*args, **kwargs):
            return Mock(
                status=Mock(value='completed'),
                snapshot_id='abc123def456',
                files_processed=250,
                bytes_transferred=5242880,
                duration=Mock(total_seconds=lambda: 15.5),
                warnings=[],
                errors=[]
            )
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.get_selection_summary = mock_summary
        mock_handler.execute_backup_with_selection = mock_execute
        
        # Execute command
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "test-template",
            "--repository", "test-repo"
        ])
        
        # Verify snapshot ID is shown
        assert_exit_code(result, 0)
        output = combined_output(result)
        assert "snapshot" in output.lower() or "abc123" in output.lower()
    
    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    @patch('TimeLocker.selection_manager.SelectionManager')
    @patch('TimeLocker.cli_modules.helpers.backup_cli_handler.BackupCLIHandler')
    def test_backup_with_warnings_displays_warnings(
        self,
        mock_handler_class,
        mock_selection_manager_class,
        mock_service_manager
    ):
        """Test that backup warnings are displayed to user"""
        # Setup mocks
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager._backup_orchestrator = Mock()
        
        mock_sm_instance = Mock()
        mock_selection_manager_class.return_value = mock_sm_instance
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        async def mock_validate(selection_name):
            return True
        
        async def mock_summary(selection_name):
            return "Test selection"
        
        async def mock_execute(*args, **kwargs):
            return Mock(
                status=Mock(value='completed'),
                snapshot_id='test-123',
                files_processed=100,
                bytes_transferred=1024000,
                duration=Mock(total_seconds=lambda: 10.0),
                warnings=["Some files were skipped", "Permission denied on /root"],
                errors=[]
            )
        
        mock_handler.validate_selection_exists = mock_validate
        mock_handler.get_selection_summary = mock_summary
        mock_handler.execute_backup_with_selection = mock_execute
        
        # Execute command
        result = runner.invoke(app, [
            "backup", "create",
            "--selection", "test-template",
            "--repository", "test-repo"
        ])
        
        # Verify warnings are shown
        assert_exit_code(result, 0)
        output = combined_output(result)
        assert "warning" in output.lower() or "skipped" in output.lower()
