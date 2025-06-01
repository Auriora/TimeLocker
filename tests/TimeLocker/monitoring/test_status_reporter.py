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

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock

from TimeLocker.monitoring import StatusReporter, OperationStatus, StatusLevel


class TestStatusReporter:
    """Test suite for StatusReporter"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.status_reporter = StatusReporter(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test status reporter initialization"""
        assert self.status_reporter.config_dir.exists()
        assert self.status_reporter.status_log_file.parent.exists()
        assert self.status_reporter.current_operations_file.parent.exists()

    def test_start_operation(self):
        """Test starting a new operation"""
        operation_id = "test_op_001"
        operation_type = "backup"
        repository_id = "test_repo"
        metadata = {"test": "data"}

        status = self.status_reporter.start_operation(
                operation_id=operation_id,
                operation_type=operation_type,
                repository_id=repository_id,
                metadata=metadata
        )

        # Verify status object
        assert status.operation_id == operation_id
        assert status.operation_type == operation_type
        assert status.repository_id == repository_id
        assert status.status == StatusLevel.INFO
        assert status.metadata == metadata
        assert "Starting" in status.message

        # Verify operation is tracked
        current_ops = self.status_reporter.get_current_operations()
        assert len(current_ops) == 1
        assert current_ops[0].operation_id == operation_id

    def test_update_operation(self):
        """Test updating an operation"""
        # Start operation
        operation_id = "test_op_002"
        self.status_reporter.start_operation(operation_id, "backup")

        # Update operation
        updated_status = self.status_reporter.update_operation(
                operation_id=operation_id,
                status=StatusLevel.INFO,
                message="Backup in progress",
                progress_percentage=50,
                files_processed=100,
                total_files=200,
                bytes_processed=1024 * 1024,
                total_bytes=2 * 1024 * 1024,
                metadata={"additional": "info"}
        )

        # Verify updates
        assert updated_status.status == StatusLevel.INFO
        assert updated_status.message == "Backup in progress"
        assert updated_status.progress_percentage == 50
        assert updated_status.files_processed == 100
        assert updated_status.total_files == 200
        assert updated_status.bytes_processed == 1024 * 1024
        assert updated_status.total_bytes == 2 * 1024 * 1024
        assert updated_status.metadata["additional"] == "info"

    def test_update_nonexistent_operation(self):
        """Test updating a non-existent operation"""
        result = self.status_reporter.update_operation(
                operation_id="nonexistent",
                status=StatusLevel.SUCCESS,
                message="This should fail"
        )

        assert result is None

    def test_complete_operation(self):
        """Test completing an operation"""
        # Start operation
        operation_id = "test_op_003"
        self.status_reporter.start_operation(operation_id, "restore")

        # Complete operation
        final_status = self.status_reporter.complete_operation(
                operation_id=operation_id,
                status=StatusLevel.SUCCESS,
                message="Restore completed successfully",
                metadata={"files_restored": 150}
        )

        # Verify completion
        assert final_status.status == StatusLevel.SUCCESS
        assert final_status.message == "Restore completed successfully"
        assert final_status.metadata["files_restored"] == 150

        # Verify operation is no longer current
        current_ops = self.status_reporter.get_current_operations()
        assert not any(op.operation_id == operation_id for op in current_ops)

    def test_get_operation_status(self):
        """Test getting operation status"""
        # Start operation
        operation_id = "test_op_004"
        original_status = self.status_reporter.start_operation(operation_id, "check")

        # Get status
        retrieved_status = self.status_reporter.get_operation_status(operation_id)

        assert retrieved_status is not None
        assert retrieved_status.operation_id == operation_id
        assert retrieved_status.operation_type == "check"

    def test_get_operation_status_nonexistent(self):
        """Test getting status for non-existent operation"""
        status = self.status_reporter.get_operation_status("nonexistent")
        assert status is None

    def test_status_handlers(self):
        """Test status update handlers"""
        handler_called = False
        received_status = None

        def test_handler(status):
            nonlocal handler_called, received_status
            handler_called = True
            received_status = status

        # Add handler
        self.status_reporter.add_status_handler(test_handler)

        # Start operation (should trigger handler)
        operation_id = "test_op_005"
        status = self.status_reporter.start_operation(operation_id, "backup")

        # Verify handler was called
        assert handler_called
        assert received_status.operation_id == operation_id

        # Test handler removal
        self.status_reporter.remove_status_handler(test_handler)
        handler_called = False

        # Update operation (should not trigger handler)
        self.status_reporter.update_operation(operation_id, message="Updated")
        assert not handler_called

    def test_operation_history(self):
        """Test operation history retrieval"""
        # Complete some operations
        for i in range(3):
            operation_id = f"history_op_{i}"
            self.status_reporter.start_operation(operation_id, "backup", f"repo_{i}")
            self.status_reporter.complete_operation(
                    operation_id, StatusLevel.SUCCESS, f"Backup {i} completed"
            )

        # Get history
        history = self.status_reporter.get_operation_history(days=7)

        # Verify history
        assert len(history) >= 3
        operation_ids = [op.operation_id for op in history]
        assert "history_op_0" in operation_ids
        assert "history_op_1" in operation_ids
        assert "history_op_2" in operation_ids

    def test_operation_history_filtering(self):
        """Test operation history filtering"""
        # Create operations of different types
        self.status_reporter.start_operation("backup_op", "backup", "repo1")
        self.status_reporter.complete_operation("backup_op", StatusLevel.SUCCESS, "Done")

        self.status_reporter.start_operation("restore_op", "restore", "repo2")
        self.status_reporter.complete_operation("restore_op", StatusLevel.SUCCESS, "Done")

        # Filter by operation type
        backup_history = self.status_reporter.get_operation_history(
                days=7, operation_type="backup"
        )
        restore_history = self.status_reporter.get_operation_history(
                days=7, operation_type="restore"
        )

        # Verify filtering
        assert len(backup_history) >= 1
        assert len(restore_history) >= 1
        assert all(op.operation_type == "backup" for op in backup_history)
        assert all(op.operation_type == "restore" for op in restore_history)

        # Filter by repository
        repo1_history = self.status_reporter.get_operation_history(
                days=7, repository_id="repo1"
        )

        assert len(repo1_history) >= 1
        assert all(op.repository_id == "repo1" for op in repo1_history)

    def test_status_summary(self):
        """Test status summary generation"""
        # Create operations with different statuses
        operations = [
                ("op1", "backup", StatusLevel.SUCCESS),
                ("op2", "backup", StatusLevel.ERROR),
                ("op3", "restore", StatusLevel.SUCCESS),
                ("op4", "check", StatusLevel.WARNING)
        ]

        for op_id, op_type, status in operations:
            self.status_reporter.start_operation(op_id, op_type, "test_repo")
            self.status_reporter.complete_operation(op_id, status, f"{op_type} completed")

        # Get summary
        summary = self.status_reporter.get_status_summary(days=7)

        # Verify summary structure
        assert "period_days" in summary
        assert "total_operations" in summary
        assert "by_type" in summary
        assert "by_status" in summary
        assert "by_repository" in summary
        assert "current_operations" in summary
        assert "generated_at" in summary

        # Verify summary content
        assert summary["total_operations"] >= 4
        assert summary["by_type"]["backup"] >= 2
        assert summary["by_type"]["restore"] >= 1
        assert summary["by_status"]["success"] >= 2
        assert summary["by_status"]["error"] >= 1

    def test_operation_status_serialization(self):
        """Test OperationStatus serialization"""
        status = OperationStatus(
                operation_id="test_serialization",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Test message",
                timestamp=datetime.now(),
                repository_id="test_repo",
                progress_percentage=75,
                files_processed=100,
                total_files=150,
                metadata={"test": "data"}
        )

        # Test to_dict
        status_dict = status.to_dict()
        assert status_dict["operation_id"] == "test_serialization"
        assert status_dict["status"] == "success"
        assert isinstance(status_dict["timestamp"], str)

        # Test from_dict
        restored_status = OperationStatus.from_dict(status_dict)
        assert restored_status.operation_id == status.operation_id
        assert restored_status.status == status.status
        assert restored_status.timestamp.replace(microsecond=0) == status.timestamp.replace(microsecond=0)

    def test_progress_estimation(self):
        """Test progress estimation for completion time"""
        # Start operation with a start time in the past to ensure meaningful elapsed time
        operation_id = "progress_test"
        start_time = datetime.now() - timedelta(seconds=10)  # 10 seconds ago

        self.status_reporter.start_operation(
                operation_id, "backup", metadata={"start_time": start_time.isoformat()}
        )

        # Update with progress
        before_update = datetime.now()
        updated_status = self.status_reporter.update_operation(
                operation_id=operation_id,
                progress_percentage=25
        )

        # Should have estimated completion time
        assert updated_status.estimated_completion is not None
        # Use a more lenient check - estimated completion should be at least close to now
        # Allow for small timing differences by checking it's not more than 1 second in the past
        assert updated_status.estimated_completion >= before_update - timedelta(seconds=1)

    def test_persistence(self):
        """Test operation persistence across service restarts"""
        # Start operation
        operation_id = "persistence_test"
        self.status_reporter.start_operation(operation_id, "backup")

        # Create new status reporter (simulating restart)
        new_reporter = StatusReporter(self.temp_dir)

        # Verify operation was loaded
        current_ops = new_reporter.get_current_operations()
        assert len(current_ops) >= 1
        assert any(op.operation_id == operation_id for op in current_ops)

    def test_concurrent_operations(self):
        """Test handling multiple concurrent operations"""
        operation_ids = ["concurrent_1", "concurrent_2", "concurrent_3"]

        # Start multiple operations
        for op_id in operation_ids:
            self.status_reporter.start_operation(op_id, "backup", f"repo_{op_id}")

        # Verify all are tracked
        current_ops = self.status_reporter.get_current_operations()
        current_op_ids = [op.operation_id for op in current_ops]

        for op_id in operation_ids:
            assert op_id in current_op_ids

        # Complete one operation
        self.status_reporter.complete_operation(
                operation_ids[0], StatusLevel.SUCCESS, "Completed"
        )

        # Verify only two remain
        current_ops = self.status_reporter.get_current_operations()
        assert len(current_ops) == 2
        assert operation_ids[0] not in [op.operation_id for op in current_ops]
