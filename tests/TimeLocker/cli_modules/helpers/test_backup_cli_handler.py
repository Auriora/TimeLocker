"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

"""
Tests for BackupCLIHandler.

This module tests the CLI handler for backup operations with data selection integration.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from pathlib import Path

from TimeLocker.cli_modules.helpers.backup_cli_handler import (
    BackupCLIHandler,
    BackupCLIHandlerError,
    SelectionTemplateNotFoundError,
    InvalidSelectionConfigError
)
from TimeLocker.selection_manager import SelectionManager
from TimeLocker.interfaces.backup_orchestrator import IBackupOrchestrator, BackupResult, BackupStatus
from TimeLocker.interfaces.data_models import ExecutionMode
from TimeLocker.selection_models import SelectionConfig, ValidationResult, ValidationError


class TestBackupCLIHandlerInitialization:
    """Test BackupCLIHandler initialization"""
    
    def test_init_with_valid_dependencies(self):
        """Test initialization with valid dependencies"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        assert handler.selection_manager is selection_manager
        assert handler.backup_orchestrator is backup_orchestrator
    
    def test_init_with_none_selection_manager(self):
        """Test initialization fails with None selection_manager"""
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        with pytest.raises(ValueError, match="selection_manager cannot be None"):
            BackupCLIHandler(None, backup_orchestrator)
    
    def test_init_with_none_backup_orchestrator(self):
        """Test initialization fails with None backup_orchestrator"""
        selection_manager = Mock(spec=SelectionManager)
        
        with pytest.raises(ValueError, match="backup_orchestrator cannot be None"):
            BackupCLIHandler(selection_manager, None)


class TestValidateSelectionExists:
    """Test validate_selection_exists method"""
    
    def test_validate_existing_template(self):
        """Test validation of existing template"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        # Mock template manager
        template_manager = Mock()
        template_manager.get_template.return_value = Mock()
        selection_manager.template_manager = template_manager
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        result = handler.validate_selection_exists("test-template")
        
        assert result is True
        template_manager.get_template.assert_called_once_with("test-template")
    
    def test_validate_nonexistent_template(self):
        """Test validation of non-existent template"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        # Mock template manager
        template_manager = Mock()
        template_manager.get_template.return_value = None
        selection_manager.template_manager = template_manager
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        result = handler.validate_selection_exists("nonexistent")
        
        assert result is False
    
    def test_validate_empty_name(self):
        """Test validation with empty template name"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        result = handler.validate_selection_exists("")
        
        assert result is False


class TestGetSelectionSummary:
    """Test get_selection_summary method"""
    
    def test_get_summary_for_existing_template(self):
        """Test getting summary for existing template"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        # Mock template with configuration
        template = Mock()
        config = Mock(spec=SelectionConfig)
        config.include_paths = [Path("/home/user")]
        config.exclude_paths = [Path("/home/user/.cache")]
        config.include_patterns = []
        config.exclude_patterns = ["*.tmp"]
        template.config = config
        
        template_manager = Mock()
        template_manager.get_template.return_value = template
        selection_manager.template_manager = template_manager
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        summary = handler.get_selection_summary("test-template")
        
        assert "test-template" in summary
        assert "Include paths: 1" in summary
        assert "Exclude paths: 1" in summary
        assert "Exclude patterns: 1" in summary
    
    def test_get_summary_for_nonexistent_template(self):
        """Test getting summary for non-existent template"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        template_manager = Mock()
        template_manager.get_template.return_value = None
        selection_manager.template_manager = template_manager
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        with pytest.raises(SelectionTemplateNotFoundError, match="not found"):
            handler.get_selection_summary("nonexistent")


class TestExecuteBackupWithSelection:
    """Test execute_backup_with_selection method"""
    
    @pytest.mark.asyncio
    async def test_execute_with_valid_template(self):
        """Test executing backup with valid template"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        # Mock template
        template = Mock()
        config = Mock(spec=SelectionConfig)
        config.include_paths = [Path("/home/user")]
        config.exclude_paths = []
        config.include_patterns = []
        config.exclude_patterns = []
        template.config = config
        
        template_manager = Mock()
        template_manager.get_template.return_value = template
        selection_manager.template_manager = template_manager
        
        # Mock validation
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        selection_manager.validate_selection = AsyncMock(return_value=validation_result)
        selection_manager.create_selection = AsyncMock(return_value=Mock())
        
        # Mock backup execution
        backup_result = BackupResult(
            status=BackupStatus.COMPLETED,
            repository_name="test-repo",
            target_names=[],
            snapshot_id="abc123"
        )
        backup_orchestrator.execute_backup_job.return_value = backup_result
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        result = await handler.execute_backup_with_selection(
            selection_name="test-template",
            repository="test-repo"
        )
        
        assert result.status == BackupStatus.COMPLETED
        assert result.snapshot_id == "abc123"
        backup_orchestrator.execute_backup_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_nonexistent_template(self):
        """Test executing backup with non-existent template"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        template_manager = Mock()
        template_manager.get_template.return_value = None
        selection_manager.template_manager = template_manager
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        with pytest.raises(SelectionTemplateNotFoundError):
            await handler.execute_backup_with_selection(
                selection_name="nonexistent",
                repository="test-repo"
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_template_config(self):
        """Test executing backup with invalid template configuration"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        # Mock template
        template = Mock()
        config = Mock(spec=SelectionConfig)
        template.config = config
        
        template_manager = Mock()
        template_manager.get_template.return_value = template
        selection_manager.template_manager = template_manager
        
        # Mock validation with errors
        validation_error = ValidationError(
            error_type="missing_include_paths",
            message="At least one include path is required"
        )
        validation_result = ValidationResult(
            is_valid=False,
            errors=[validation_error],
            warnings=[]
        )
        selection_manager.validate_selection = AsyncMock(return_value=validation_result)
        selection_manager.create_selection = AsyncMock(return_value=Mock())
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        with pytest.raises(InvalidSelectionConfigError):
            await handler.execute_backup_with_selection(
                selection_name="invalid-template",
                repository="test-repo"
            )


class TestGetAvailableTemplates:
    """Test get_available_templates method"""
    
    def test_get_available_templates(self):
        """Test getting list of available templates"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        # Mock templates
        template1 = Mock()
        template1.name = "template1"
        template2 = Mock()
        template2.name = "template2"
        
        template_manager = Mock()
        template_manager.list_templates.return_value = [template1, template2]
        selection_manager.template_manager = template_manager
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        templates = handler.get_available_templates()
        
        assert templates == ["template1", "template2"]
    
    def test_get_available_templates_empty(self):
        """Test getting empty list when no templates exist"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        template_manager = Mock()
        template_manager.list_templates.return_value = []
        selection_manager.template_manager = template_manager
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        templates = handler.get_available_templates()
        
        assert templates == []


class TestSuggestTemplateCreation:
    """Test suggest_template_creation method"""
    
    def test_suggest_with_available_templates(self):
        """Test suggestion message with available templates"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        # Mock templates
        templates = [Mock(name=f"template{i}") for i in range(3)]
        for i, t in enumerate(templates):
            t.name = f"template{i}"
        
        template_manager = Mock()
        template_manager.list_templates.return_value = templates
        selection_manager.template_manager = template_manager
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        message = handler.suggest_template_creation("missing-template")
        
        assert "missing-template" in message
        assert "Available templates:" in message
        assert "template0" in message
        assert "tl selections create" in message
    
    def test_suggest_with_no_available_templates(self):
        """Test suggestion message with no available templates"""
        selection_manager = Mock(spec=SelectionManager)
        backup_orchestrator = Mock(spec=IBackupOrchestrator)
        
        template_manager = Mock()
        template_manager.list_templates.return_value = []
        selection_manager.template_manager = template_manager
        
        handler = BackupCLIHandler(selection_manager, backup_orchestrator)
        
        message = handler.suggest_template_creation("missing-template")
        
        assert "missing-template" in message
        assert "Available templates:" not in message
        assert "tl selections create" in message
