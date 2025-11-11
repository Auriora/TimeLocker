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
    IntegrityChecker,
    IntegrityLevel,
    IntegrityCheckResult,
    IntegrityIssue,
    CheckInterval
)


class TestIntegrityIssue:
    """Test suite for IntegrityIssue dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_integrity_issue_creation(self):
        """Test creating an IntegrityIssue instance"""
        issue = IntegrityIssue(
            issue_id="issue_001",
            severity="high",
            description="Corrupted data block detected",
            affected_snapshots=["snap_001", "snap_002"],
            detected_at=datetime.now(),
            suggested_action="Run repository repair"
        )

        assert issue.issue_id == "issue_001"
        assert issue.severity == "high"
        assert len(issue.affected_snapshots) == 2

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_integrity_issue_to_dict(self):
        """Test converting IntegrityIssue to dictionary"""
        issue = IntegrityIssue(
            issue_id="issue_001",
            severity="critical",
            description="Data corruption",
            affected_snapshots=["snap_001"],
            detected_at=datetime.now(),
            suggested_action="Restore from backup"
        )

        issue_dict = issue.to_dict()
        assert issue_dict["issue_id"] == "issue_001"
        assert issue_dict["severity"] == "critical"

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_integrity_issue_from_dict(self):
        """Test creating IntegrityIssue from dictionary"""
        timestamp = datetime.now()
        data = {
            "issue_id": "issue_001",
            "severity": "medium",
            "description": "Minor inconsistency",
            "affected_snapshots": ["snap_001"],
            "detected_at": timestamp.isoformat(),
            "suggested_action": "Monitor",
            "metadata": None
        }

        issue = IntegrityIssue.from_dict(data)
        assert issue.issue_id == "issue_001"
        assert issue.severity == "medium"


class TestIntegrityCheckResult:
    """Test suite for IntegrityCheckResult dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_integrity_check_result_creation(self):
        """Test creating an IntegrityCheckResult instance"""
        result = IntegrityCheckResult(
            check_id="check_001",
            repository_id="test_repo",
            check_time=datetime.now(),
            status=IntegrityLevel.HEALTHY,
            duration=timedelta(minutes=5),
            issues_found=[],
            snapshots_checked=10,
            data_verified_bytes=1024 * 1024 * 1024
        )

        assert result.check_id == "check_001"
        assert result.status == IntegrityLevel.HEALTHY
        assert result.snapshots_checked == 10

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_integrity_check_result_with_issues(self):
        """Test IntegrityCheckResult with issues"""
        issue = IntegrityIssue(
            issue_id="issue_001",
            severity="high",
            description="Data corruption",
            affected_snapshots=["snap_001"],
            detected_at=datetime.now(),
            suggested_action="Repair"
        )

        result = IntegrityCheckResult(
            check_id="check_001",
            repository_id="test_repo",
            check_time=datetime.now(),
            status=IntegrityLevel.ERROR,
            duration=timedelta(minutes=5),
            issues_found=[issue],
            snapshots_checked=10,
            data_verified_bytes=1024 * 1024 * 1024
        )

        assert len(result.issues_found) == 1
        assert result.status == IntegrityLevel.ERROR

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_integrity_check_result_to_dict(self):
        """Test converting IntegrityCheckResult to dictionary"""
        result = IntegrityCheckResult(
            check_id="check_001",
            repository_id="test_repo",
            check_time=datetime.now(),
            status=IntegrityLevel.HEALTHY,
            duration=timedelta(minutes=5),
            issues_found=[],
            snapshots_checked=10,
            data_verified_bytes=1024 * 1024 * 1024
        )

        result_dict = result.to_dict()
        assert result_dict["check_id"] == "check_001"
        assert result_dict["status"] == "healthy"
        assert result_dict["snapshots_checked"] == 10
