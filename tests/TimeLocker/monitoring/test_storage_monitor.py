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
from datetime import datetime
from unittest.mock import Mock, patch

from TimeLocker.monitoring import (
    StorageMonitor,
    StorageUsage,
    CapacityWarning,
    WarningLevel
)


class TestStorageUsage:
    """Test suite for StorageUsage dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_storage_usage_creation(self):
        """Test creating a StorageUsage instance"""
        usage = StorageUsage(
            repository_id="test_repo",
            used_bytes=1024 * 1024 * 1024,
            available_bytes=5 * 1024 * 1024 * 1024,
            total_bytes=10 * 1024 * 1024 * 1024,
            usage_percentage=10.0,
            deduplication_ratio=2.5,
            compression_ratio=1.8,
            last_updated=datetime.now()
        )

        assert usage.repository_id == "test_repo"
        assert usage.used_bytes == 1024 * 1024 * 1024
        assert usage.usage_percentage == 10.0

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_storage_usage_to_dict(self):
        """Test converting StorageUsage to dictionary"""
        usage = StorageUsage(
            repository_id="test_repo",
            used_bytes=1024 * 1024 * 1024,
            available_bytes=5 * 1024 * 1024 * 1024,
            total_bytes=10 * 1024 * 1024 * 1024,
            usage_percentage=10.0,
            deduplication_ratio=2.5,
            compression_ratio=1.8,
            last_updated=datetime.now()
        )

        usage_dict = usage.to_dict()
        assert usage_dict["repository_id"] == "test_repo"
        assert "last_updated" in usage_dict

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_storage_usage_from_dict(self):
        """Test creating StorageUsage from dictionary"""
        timestamp = datetime.now()
        data = {
            "repository_id": "test_repo",
            "used_bytes": 1024 * 1024 * 1024,
            "available_bytes": 5 * 1024 * 1024 * 1024,
            "total_bytes": 10 * 1024 * 1024 * 1024,
            "usage_percentage": 10.0,
            "deduplication_ratio": 2.5,
            "compression_ratio": 1.8,
            "last_updated": timestamp.isoformat()
        }

        usage = StorageUsage.from_dict(data)
        assert usage.repository_id == "test_repo"
        assert usage.used_bytes == 1024 * 1024 * 1024


class TestCapacityWarning:
    """Test suite for CapacityWarning dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_capacity_warning_creation(self):
        """Test creating a CapacityWarning instance"""
        warning = CapacityWarning(
            repository_id="test_repo",
            level=WarningLevel.WARNING,
            message="Storage capacity at 85%",
            usage_percentage=85.0,
            used_bytes=8.5 * 1024 * 1024 * 1024,
            available_bytes=1.5 * 1024 * 1024 * 1024,
            timestamp=datetime.now()
        )

        assert warning.repository_id == "test_repo"
        assert warning.level == WarningLevel.WARNING
        assert warning.usage_percentage == 85.0

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_capacity_warning_to_dict(self):
        """Test converting CapacityWarning to dictionary"""
        warning = CapacityWarning(
            repository_id="test_repo",
            level=WarningLevel.CRITICAL,
            message="Storage capacity critical",
            usage_percentage=95.0,
            used_bytes=9.5 * 1024 * 1024 * 1024,
            available_bytes=0.5 * 1024 * 1024 * 1024,
            timestamp=datetime.now()
        )

        warning_dict = warning.to_dict()
        assert warning_dict["level"] == "critical"
        assert warning_dict["usage_percentage"] == 95.0
