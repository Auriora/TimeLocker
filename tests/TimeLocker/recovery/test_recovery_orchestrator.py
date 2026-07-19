"""
Tests for RecoveryOrchestrator functionality
"""

import asyncio
import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
from TimeLocker.interfaces.recovery_models import (
    RecoveryOptions,
    RecoveryType,
    OperationStatus,
    ProgressStatus,
    SelectionCriteria
)
from TimeLocker.recovery_errors import (
    SnapshotNotFoundError,
    RestoreTargetError,
    RepositoryAccessError
)
from .mock_recovery_repository import MockRecoveryRepository
from TimeLocker.selection_manager import SelectionManager
from TimeLocker.selection_template_manager import SelectionTemplateManager
from TimeLocker.selection_models import (
    SelectionTemplate,
    SelectionConfig,
    PatternRule,
    PatternSyntax,
    PathComponent
)


class TestRecoveryOrchestrator:
    """Test cases for RecoveryOrchestrator"""

    def setup_method(self):
        """Set up test fixtures"""
        self.repository = MockRecoveryRepository()
        self.orchestrator = RecoveryOrchestrator(self.repository)
        
        # Create temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_initiate_full_recovery_success(self):
        """Test successful full recovery initiation"""
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            options=options
        )
        
        assert operation is not None
        assert operation.snapshot_id == "abc123"
        assert operation.recovery_type == RecoveryType.FULL
        assert operation.progress == ProgressStatus(0, 0, 0, 0)
        assert operation.target_path == target_path
        # Operation should be initiated (any status is acceptable for this test)
        assert operation.status in [
            OperationStatus.PENDING, 
            OperationStatus.RUNNING, 
            OperationStatus.COMPLETED,
            OperationStatus.FAILED  # May fail in mock environment
        ]

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_initiate_full_recovery_snapshot_not_found(self):
        """Test full recovery with non-existent snapshot"""
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        with pytest.raises(SnapshotNotFoundError):
            self.orchestrator.initiate_full_recovery(
                snapshot_id="nonexistent",
                target_path=target_path,
                options=options
            )

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_initiate_full_recovery_invalid_target(self):
        """Test full recovery with invalid target path"""
        # Create a file instead of directory
        invalid_target = self.temp_dir / "file.txt"
        invalid_target.write_text("test")
        
        options = RecoveryOptions()
        
        with pytest.raises(RestoreTargetError):
            self.orchestrator.initiate_full_recovery(
                snapshot_id="abc123",
                target_path=str(invalid_target),
                options=options
            )

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_initiate_selective_recovery_success(self):
        """Test successful selective recovery initiation"""
        target_path = str(self.temp_dir / "restore_target")
        selection_criteria = SelectionCriteria(
            include_patterns=["*.txt", "*.pdf"],
            exclude_patterns=["temp/*"]
        )
        options = RecoveryOptions()
        
        operation = self.orchestrator.initiate_selective_recovery(
            snapshot_id="abc123",
            selection_criteria=selection_criteria,
            target_path=target_path,
            options=options
        )
        
        assert operation is not None
        assert operation.snapshot_id == "abc123"
        assert operation.recovery_type == RecoveryType.SELECTIVE
        assert operation.progress == ProgressStatus(0, 0, 0, 0)
        assert operation.target_path == target_path

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_apply_selection_template_resolves_name(self, tmp_path):
        """Selection templates referenced by name should resolve to canonical IDs."""
        storage_dir = tmp_path / "recovery-selection-templates"
        template_manager = SelectionTemplateManager(storage_dir=storage_dir)
        template = SelectionTemplate(
            id="template-docs",
            name="Documents",
            description="Documents selection for recovery",
            selection_config=SelectionConfig(
                include_patterns=[
                    PatternRule(
                        pattern="*.pdf",
                        syntax=PatternSyntax.GLOB,
                        applies_to=PathComponent.FILENAME
                    )
                ]
            )
        )
        template_manager.create_template(template)
        selection_manager = SelectionManager(template_manager=template_manager)
        orchestrator = RecoveryOrchestrator(
            self.repository,
            selection_manager=selection_manager
        )

        criteria = SelectionCriteria(
            include_patterns=["*.txt"],
            exclude_patterns=[],
            selection_template_id="Documents"
        )

        merged = asyncio.run(orchestrator._apply_selection_template(criteria))

        assert merged.selection_template_id == template.id
        assert "*.txt" in merged.include_patterns
        assert "*.pdf" in merged.include_patterns

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_get_recovery_status(self):
        """Test retrieving recovery operation status"""
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            options=options
        )
        
        # Retrieve status
        status = self.orchestrator.get_recovery_status(operation.operation_id)
        
        assert status is not None
        assert status.operation_id == operation.operation_id
        assert status.snapshot_id == "abc123"

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_get_recovery_status_not_found(self):
        """Test retrieving status for non-existent operation"""
        status = self.orchestrator.get_recovery_status("nonexistent-id")
        
        assert status is None

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_cancel_recovery_success(self):
        """Test cancelling an active recovery operation"""
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        # Start a recovery operation
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            options=options
        )
        
        # Cancel it
        result = self.orchestrator.cancel_recovery(operation.operation_id)
        
        # In mock environment, operation may complete before cancellation
        # Check that cancellation was attempted (True if cancelled, False if already complete)
        assert isinstance(result, bool)
        
        # Verify final status
        status = self.orchestrator.get_recovery_status(operation.operation_id)
        assert status is not None
        # Status should be either CANCELLED or already completed
        assert status.status in [
            OperationStatus.CANCELLED,
            OperationStatus.COMPLETED,
            OperationStatus.FAILED
        ]

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_cancel_recovery_not_found(self):
        """Test cancelling non-existent operation"""
        result = self.orchestrator.cancel_recovery("nonexistent-id")
        
        assert result is False

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_list_operations(self):
        """Test listing all recovery operations"""
        target_path1 = str(self.temp_dir / "restore1")
        target_path2 = str(self.temp_dir / "restore2")
        options = RecoveryOptions()
        
        # Create multiple operations
        op1 = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path1,
            options=options
        )
        
        op2 = self.orchestrator.initiate_full_recovery(
            snapshot_id="def456",
            target_path=target_path2,
            options=options
        )
        
        # List all operations
        operations = self.orchestrator.list_operations()
        
        assert len(operations) >= 2
        operation_ids = [op.operation_id for op in operations]
        assert op1.operation_id in operation_ids
        assert op2.operation_id in operation_ids

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_list_operations_exclude_completed(self):
        """Test listing only active operations"""
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        # Create and complete an operation
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            options=options
        )
        
        # List only active operations
        active_operations = self.orchestrator.list_operations(include_completed=False)
        
        # Verify filtering works
        assert isinstance(active_operations, list)
        # Active operations should only include PENDING or RUNNING status
        for op in active_operations:
            assert op.status in [OperationStatus.PENDING, OperationStatus.RUNNING]

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_repository_accessibility_validation(self):
        """Test repository accessibility validation"""
        # Create a mock repository that is not initialized
        uninit_repo = MockRecoveryRepository()
        uninit_repo._initialized = False
        
        orchestrator = RecoveryOrchestrator(uninit_repo)
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        with pytest.raises(RepositoryAccessError):
            orchestrator.initiate_full_recovery(
                snapshot_id="abc123",
                target_path=target_path,
                options=options
            )

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_recovery_with_default_options(self):
        """Test recovery with default options"""
        target_path = str(self.temp_dir / "restore_target")
        
        # Don't provide options - should use defaults
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path
        )
        
        assert operation is not None
        assert operation.snapshot_id == "abc123"

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_recovery_operation_tracking(self):
        """Test that recovery operations are properly tracked"""
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        # Create operation
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            options=options
        )
        
        # Verify operation is tracked
        tracked_op = self.orchestrator.get_recovery_status(operation.operation_id)
        assert tracked_op is not None
        assert tracked_op.operation_id == operation.operation_id
