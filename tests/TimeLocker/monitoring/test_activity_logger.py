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

from TimeLocker.monitoring import (
    ActivityLogger,
    LogLevel,
    LogEntry,
    OperationStatus,
    StatusLevel
)


class TestLogEntry:
    """Test suite for LogEntry dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_log_entry_creation(self):
        """Test creating a LogEntry instance"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            operation_type="backup",
            operation_id="test_op",
            repository_id="test_repo",
            message="Test message",
            details={"key": "value"}
        )

        assert entry.level == LogLevel.INFO
        assert entry.operation_type == "backup"
        assert entry.message == "Test message"
        assert entry.details["key"] == "value"

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_log_entry_to_dict(self):
        """Test converting LogEntry to dictionary"""
        timestamp = datetime.now()
        entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.ERROR,
            operation_type="restore",
            operation_id="op_001",
            repository_id="repo_001",
            message="Error occurred",
            details={"error": "test"},
            error_context={"type": "TestError"},
            troubleshooting_suggestions=["Check logs"]
        )

        entry_dict = entry.to_dict()

        assert entry_dict["timestamp"] == timestamp.isoformat()
        assert entry_dict["level"] == "error"
        assert entry_dict["operation_type"] == "restore"
        assert entry_dict["message"] == "Error occurred"
        assert "error_context" in entry_dict
        assert "troubleshooting_suggestions" in entry_dict

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_log_entry_from_dict(self):
        """Test creating LogEntry from dictionary"""
        timestamp = datetime.now()
        data = {
            "timestamp": timestamp.isoformat(),
            "level": "warning",
            "operation_type": "check",
            "operation_id": "check_001",
            "repository_id": "repo_001",
            "message": "Warning message",
            "details": {"warning": "test"}
        }

        entry = LogEntry.from_dict(data)

        assert entry.level == LogLevel.WARNING
        assert entry.operation_type == "check"
        assert entry.message == "Warning message"


class TestActivityLogger:
    """Test suite for ActivityLogger"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = ActivityLogger(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_initialization(self):
        """Test ActivityLogger initialization"""
        assert self.logger.log_dir.exists()
        assert self.logger.current_log.parent.exists()
        assert self.logger.user_friendly_log.parent.exists()
        assert self.logger.log_level == LogLevel.INFO

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_set_log_level(self):
        """Test setting log level"""
        self.logger.set_log_level(LogLevel.DEBUG)
        assert self.logger.log_level == LogLevel.DEBUG

        self.logger.set_log_level(LogLevel.ERROR)
        assert self.logger.log_level == LogLevel.ERROR

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_log_backup_event_success(self):
        """Test logging successful backup event"""
        status = OperationStatus(
            operation_id="backup_001",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Backup completed successfully",
            timestamp=datetime.now(),
            repository_id="test_repo",
            progress_percentage=100,
            files_processed=150,
            total_files=150,
            bytes_processed=1024 * 1024 * 50
        )

        self.logger.log_backup_event(status)

        assert self.logger.current_log.exists()
        assert self.logger.user_friendly_log.exists()

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_log_backup_event_error(self):
        """Test logging backup error event"""
        status = OperationStatus(
            operation_id="backup_002",
            operation_type="backup",
            status=StatusLevel.ERROR,
            message="Backup failed due to permission error",
            timestamp=datetime.now(),
            repository_id="test_repo"
        )

        self.logger.log_backup_event(status)

        with open(self.logger.current_log, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            assert log_data["level"] == "error"

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_log_error(self):
        """Test logging errors with context"""
        error = ValueError("Test error")
        context = {
            "operation_type": "backup",
            "operation_id": "op_001",
            "repository_id": "test_repo"
        }

        self.logger.log_error(error, context)

        with open(self.logger.current_log, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            assert log_data["level"] == "error"
            assert "error_context" in log_data

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_recent_logs(self):
        """Test retrieving recent log entries"""
        for i in range(3):
            status = OperationStatus(
                operation_id=f"op_{i}",
                operation_type="backup",
                status=StatusLevel.INFO,
                message=f"Backup {i}",
                timestamp=datetime.now()
            )
            self.logger.log_backup_event(status)

        recent_logs = self.logger.get_recent_logs(hours=24)
        assert len(recent_logs) >= 3
