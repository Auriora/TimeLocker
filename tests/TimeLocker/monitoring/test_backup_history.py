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
from pathlib import Path
from datetime import datetime, timedelta

from TimeLocker.monitoring import (
    BackupHistory,
    BackupRecord,
    BackupStatus,
    HistoryFilters,
    PerformanceTrends
)


class TestBackupRecord:
    """Test suite for BackupRecord dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_backup_record_creation(self):
        """Test creating a BackupRecord instance"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)
        
        record = BackupRecord(
            operation_id="backup_001",
            repository_id="test_repo",
            start_time=start_time,
            end_time=end_time,
            status=BackupStatus.SUCCESS,
            files_processed=100,
            bytes_transferred=1024 * 1024 * 500,
            duration_seconds=300.0,
            snapshot_id="snap_001"
        )

        assert record.operation_id == "backup_001"
        assert record.status == BackupStatus.SUCCESS
        assert record.files_processed == 100

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_duration_formatted(self):
        """Test formatted duration string"""
        record = BackupRecord(
            operation_id="test",
            repository_id="repo",
            start_time=datetime.now(),
            end_time=datetime.now(),
            status=BackupStatus.SUCCESS,
            files_processed=0,
            bytes_transferred=0,
            duration_seconds=3665.0
        )

        formatted = record.duration_formatted
        assert "1h" in formatted
        assert "1m" in formatted
        assert "5s" in formatted

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_bytes_transferred_formatted(self):
        """Test formatted bytes transferred string"""
        record = BackupRecord(
            operation_id="test",
            repository_id="repo",
            start_time=datetime.now(),
            end_time=datetime.now(),
            status=BackupStatus.SUCCESS,
            files_processed=0,
            bytes_transferred=1024 * 1024 * 1024,
            duration_seconds=60.0
        )

        formatted = record.bytes_transferred_formatted
        assert "GB" in formatted

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_throughput_calculation(self):
        """Test throughput calculation"""
        record = BackupRecord(
            operation_id="test",
            repository_id="repo",
            start_time=datetime.now(),
            end_time=datetime.now(),
            status=BackupStatus.SUCCESS,
            files_processed=0,
            bytes_transferred=1024 * 1024 * 100,
            duration_seconds=10.0
        )

        throughput = record.throughput_mbps
        assert throughput == 10.0


class TestBackupHistory:
    """Test suite for BackupHistory"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.history = BackupHistory(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_initialization(self):
        """Test BackupHistory initialization"""
        assert self.history.config_dir.exists()
        assert self.history.history_db.exists()
        assert self.history.retention_days == 90

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_record_backup_operation(self):
        """Test recording a backup operation"""
        record = BackupRecord(
            operation_id="backup_001",
            repository_id="test_repo",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=5),
            status=BackupStatus.SUCCESS,
            files_processed=100,
            bytes_transferred=1024 * 1024 * 500,
            duration_seconds=300.0,
            snapshot_id="snap_001"
        )

        self.history.record_backup_operation(record)

        retrieved = self.history.get_backup_by_id("backup_001")
        assert retrieved is not None
        assert retrieved.operation_id == "backup_001"
        assert retrieved.status == BackupStatus.SUCCESS

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_backup_history(self):
        """Test retrieving backup history"""
        for i in range(3):
            record = BackupRecord(
                operation_id=f"backup_{i}",
                repository_id="test_repo",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(minutes=5),
                status=BackupStatus.SUCCESS,
                files_processed=100,
                bytes_transferred=1024 * 1024 * 100,
                duration_seconds=300.0
            )
            self.history.record_backup_operation(record)

        history = self.history.get_backup_history()
        assert len(history) == 3

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_backup_history_with_filters(self):
        """Test retrieving backup history with filters"""
        for i in range(5):
            status = BackupStatus.SUCCESS if i % 2 == 0 else BackupStatus.FAILED
            record = BackupRecord(
                operation_id=f"backup_{i}",
                repository_id=f"repo_{i % 2}",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(minutes=5),
                status=status,
                files_processed=100,
                bytes_transferred=1024 * 1024 * 100,
                duration_seconds=300.0
            )
            self.history.record_backup_operation(record)

        filters = HistoryFilters(repository_id="repo_0")
        history = self.history.get_backup_history(filters)
        assert all(r.repository_id == "repo_0" for r in history)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_latest_backup(self):
        """Test getting the latest backup"""
        for i in range(3):
            record = BackupRecord(
                operation_id=f"backup_{i}",
                repository_id="test_repo",
                start_time=datetime.now() + timedelta(minutes=i),
                end_time=datetime.now() + timedelta(minutes=i+5),
                status=BackupStatus.SUCCESS,
                files_processed=100,
                bytes_transferred=1024 * 1024 * 100,
                duration_seconds=300.0
            )
            self.history.record_backup_operation(record)

        latest = self.history.get_latest_backup()
        assert latest is not None
        assert latest.operation_id == "backup_2"

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_performance_trends(self):
        """Test getting performance trends"""
        for i in range(5):
            record = BackupRecord(
                operation_id=f"backup_{i}",
                repository_id="test_repo",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(minutes=5),
                status=BackupStatus.SUCCESS,
                files_processed=100,
                bytes_transferred=1024 * 1024 * 100,
                duration_seconds=300.0
            )
            self.history.record_backup_operation(record)

        trends = self.history.get_performance_trends(days=30)
        assert trends.total_backups == 5
        assert trends.successful_backups == 5
        assert trends.failed_backups == 0

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_export_history(self):
        """Test exporting backup history to CSV"""
        record = BackupRecord(
            operation_id="backup_001",
            repository_id="test_repo",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=5),
            status=BackupStatus.SUCCESS,
            files_processed=100,
            bytes_transferred=1024 * 1024 * 100,
            duration_seconds=300.0
        )
        self.history.record_backup_operation(record)

        output_path = self.temp_dir / "export.csv"
        result_path = self.history.export_history(output_path)

        assert result_path.exists()
        assert result_path == output_path

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_set_retention_period(self):
        """Test setting retention period"""
        self.history.set_retention_period(30)
        assert self.history.retention_days == 30

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_statistics(self):
        """Test getting backup statistics"""
        for i in range(10):
            status = BackupStatus.SUCCESS if i < 8 else BackupStatus.FAILED
            record = BackupRecord(
                operation_id=f"backup_{i}",
                repository_id="test_repo",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(minutes=5),
                status=status,
                files_processed=100,
                bytes_transferred=1024 * 1024 * 100,
                duration_seconds=300.0
            )
            self.history.record_backup_operation(record)

        stats = self.history.get_statistics()
        assert stats["total_backups"] == 10
        assert stats["successful_backups"] == 8
        assert stats["failed_backups"] == 2
        assert stats["success_rate"] == 80.0
