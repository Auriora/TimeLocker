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
from datetime import datetime, timedelta

from TimeLocker.monitoring import (
    PerformanceTracker,
    BackupPerformanceMetrics,
    PerformanceLevel
)


class TestBackupPerformanceMetrics:
    """Test suite for BackupPerformanceMetrics dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_performance_metrics_creation(self):
        """Test creating a BackupPerformanceMetrics instance"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)
        
        metrics = BackupPerformanceMetrics(
            operation_id="backup_001",
            repository_id="test_repo",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=300.0,
            files_processed=1000,
            bytes_processed=1024 * 1024 * 500,
            files_per_second=3.33,
            throughput_mbps=1.67,
            average_file_size_mb=0.5,
            performance_level=PerformanceLevel.GOOD
        )

        assert metrics.operation_id == "backup_001"
        assert metrics.files_processed == 1000
        assert metrics.performance_level == PerformanceLevel.GOOD

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_performance_metrics_to_dict(self):
        """Test converting BackupPerformanceMetrics to dictionary"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)
        
        metrics = BackupPerformanceMetrics(
            operation_id="backup_001",
            repository_id="test_repo",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=300.0,
            files_processed=1000,
            bytes_processed=1024 * 1024 * 500,
            files_per_second=3.33,
            throughput_mbps=1.67,
            average_file_size_mb=0.5,
            performance_level=PerformanceLevel.EXCELLENT
        )

        metrics_dict = metrics.to_dict()
        assert metrics_dict["operation_id"] == "backup_001"
        assert metrics_dict["performance_level"] == "excellent"

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_performance_metrics_from_dict(self):
        """Test creating BackupPerformanceMetrics from dictionary"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)
        
        data = {
            "operation_id": "backup_001",
            "repository_id": "test_repo",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": 300.0,
            "files_processed": 1000,
            "bytes_processed": 1024 * 1024 * 500,
            "files_per_second": 3.33,
            "throughput_mbps": 1.67,
            "average_file_size_mb": 0.5,
            "performance_level": "good",
            "metadata": {}
        }

        metrics = BackupPerformanceMetrics.from_dict(data)
        assert metrics.operation_id == "backup_001"
        assert metrics.performance_level == PerformanceLevel.GOOD

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_user_friendly_summary(self):
        """Test getting user-friendly performance summary"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)
        
        metrics = BackupPerformanceMetrics(
            operation_id="backup_001",
            repository_id="test_repo",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=300.0,
            files_processed=1000,
            bytes_processed=1024 * 1024 * 500,
            files_per_second=3.33,
            throughput_mbps=1.67,
            average_file_size_mb=0.5,
            performance_level=PerformanceLevel.GOOD
        )

        summary = metrics.get_user_friendly_summary()
        assert "1,000" in summary or "1000" in summary
        assert "MB/s" in summary
        assert "minutes" in summary

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_format_duration(self):
        """Test duration formatting"""
        # Test seconds
        assert "seconds" in BackupPerformanceMetrics._format_duration(45.0)
        
        # Test minutes
        assert "minutes" in BackupPerformanceMetrics._format_duration(120.0)
        
        # Test hours
        assert "hours" in BackupPerformanceMetrics._format_duration(3600.0)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_format_bytes(self):
        """Test bytes formatting"""
        # Test KB
        assert "KB" in BackupPerformanceMetrics._format_bytes(1024 * 10)
        
        # Test MB
        assert "MB" in BackupPerformanceMetrics._format_bytes(1024 * 1024 * 10)
        
        # Test GB
        assert "GB" in BackupPerformanceMetrics._format_bytes(1024 * 1024 * 1024 * 10)
