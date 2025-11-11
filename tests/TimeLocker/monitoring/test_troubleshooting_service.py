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
    TroubleshootingService,
    IssueType,
    IssueSeverity,
    DetectedIssue,
    TroubleshootingStep,
    TroubleshootingGuide,
    BackupFailure
)


class TestDetectedIssue:
    """Test suite for DetectedIssue dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_detected_issue_creation(self):
        """Test creating a DetectedIssue instance"""
        issue = DetectedIssue(
            issue_id="issue_001",
            issue_type=IssueType.BACKUP_FAILURE,
            severity=IssueSeverity.HIGH,
            title="Backup failed repeatedly",
            description="Backup has failed 3 times in the last hour",
            affected_operations=["op_001", "op_002", "op_003"],
            first_occurrence=datetime.now() - timedelta(hours=1),
            last_occurrence=datetime.now(),
            occurrence_count=3,
            repository_id="test_repo"
        )

        assert issue.issue_id == "issue_001"
        assert issue.issue_type == IssueType.BACKUP_FAILURE
        assert issue.severity == IssueSeverity.HIGH
        assert issue.occurrence_count == 3


class TestTroubleshootingStep:
    """Test suite for TroubleshootingStep dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_troubleshooting_step_creation(self):
        """Test creating a TroubleshootingStep instance"""
        step = TroubleshootingStep(
            step_number=1,
            description="Check repository connectivity",
            command="timelocker repos check test_repo",
            expected_result="Repository is accessible",
            additional_info="Ensure network connection is stable"
        )

        assert step.step_number == 1
        assert step.description == "Check repository connectivity"
        assert step.command is not None


class TestTroubleshootingGuide:
    """Test suite for TroubleshootingGuide dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_troubleshooting_guide_creation(self):
        """Test creating a TroubleshootingGuide instance"""
        steps = [
            TroubleshootingStep(
                step_number=1,
                description="Check logs",
                command="timelocker logs --recent"
            ),
            TroubleshootingStep(
                step_number=2,
                description="Verify configuration",
                command="timelocker config validate"
            )
        ]

        guide = TroubleshootingGuide(
            issue_type=IssueType.BACKUP_FAILURE,
            title="Backup Failure Troubleshooting",
            description="Steps to diagnose and fix backup failures",
            possible_causes=["Network issues", "Permission problems", "Storage full"],
            steps=steps,
            additional_resources=["https://docs.example.com/backup-troubleshooting"],
            prevention_tips=["Regular monitoring", "Automated health checks"]
        )

        assert guide.issue_type == IssueType.BACKUP_FAILURE
        assert len(guide.steps) == 2
        assert len(guide.possible_causes) == 3


class TestBackupFailure:
    """Test suite for BackupFailure dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_backup_failure_creation(self):
        """Test creating a BackupFailure instance"""
        failure = BackupFailure(
            operation_id="backup_001",
            repository_id="test_repo",
            timestamp=datetime.now(),
            error_message="Connection timeout",
            error_type="NetworkError",
            stack_trace="Traceback...",
            metadata={"retry_count": 3}
        )

        assert failure.operation_id == "backup_001"
        assert failure.error_type == "NetworkError"
        assert failure.metadata["retry_count"] == 3
