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

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class IntegrityLevel(Enum):
    """Integrity check result levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class CheckInterval(Enum):
    """Integrity check interval options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


@dataclass
class IntegrityIssue:
    """Represents an integrity issue found during checking"""
    issue_id: str
    severity: str  # critical, high, medium, low
    description: str
    affected_snapshots: List[str]
    detected_at: datetime
    suggested_action: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['detected_at'] = self.detected_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntegrityIssue':
        """Create from dictionary"""
        data['detected_at'] = datetime.fromisoformat(data['detected_at'])
        return cls(**data)


@dataclass
class IntegrityCheckResult:
    """Result of an integrity check operation"""
    check_id: str
    repository_id: str
    check_time: datetime
    status: IntegrityLevel
    duration: timedelta
    issues_found: List[IntegrityIssue]
    snapshots_checked: int
    data_verified_bytes: int
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'check_id': self.check_id,
            'repository_id': self.repository_id,
            'check_time': self.check_time.isoformat(),
            'status': self.status.value,
            'duration': self.duration.total_seconds(),
            'issues_found': [issue.to_dict() for issue in self.issues_found],
            'snapshots_checked': self.snapshots_checked,
            'data_verified_bytes': self.data_verified_bytes,
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntegrityCheckResult':
        """Create from dictionary"""
        return cls(
            check_id=data['check_id'],
            repository_id=data['repository_id'],
            check_time=datetime.fromisoformat(data['check_time']),
            status=IntegrityLevel(data['status']),
            duration=timedelta(seconds=data['duration']),
            issues_found=[IntegrityIssue.from_dict(issue) for issue in data['issues_found']],
            snapshots_checked=data['snapshots_checked'],
            data_verified_bytes=data['data_verified_bytes'],
            metadata=data.get('metadata')
        )


@dataclass
class IntegrityStatus:
    """Current integrity status for a repository"""
    repository_id: str
    last_check: Optional[datetime]
    status: IntegrityLevel
    issues_found: int
    check_duration: Optional[timedelta]
    next_scheduled_check: Optional[datetime]
    check_interval: CheckInterval
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'repository_id': self.repository_id,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'status': self.status.value,
            'issues_found': self.issues_found,
            'check_duration': self.check_duration.total_seconds() if self.check_duration else None,
            'next_scheduled_check': self.next_scheduled_check.isoformat() if self.next_scheduled_check else None,
            'check_interval': self.check_interval.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntegrityStatus':
        """Create from dictionary"""
        return cls(
            repository_id=data['repository_id'],
            last_check=datetime.fromisoformat(data['last_check']) if data.get('last_check') else None,
            status=IntegrityLevel(data['status']),
            issues_found=data['issues_found'],
            check_duration=timedelta(seconds=data['check_duration']) if data.get('check_duration') else None,
            next_scheduled_check=datetime.fromisoformat(data['next_scheduled_check']) if data.get('next_scheduled_check') else None,
            check_interval=CheckInterval(data['check_interval'])
        )


@dataclass
class RemediationGuide:
    """User-friendly guidance for integrity issues"""
    issue_summary: str
    severity: str
    affected_backups: List[str]
    recommended_actions: List[str]
    detailed_steps: List[str]
    additional_resources: List[str]
    estimated_time: str
    requires_technical_support: bool


class IntegrityChecker:
    """
    Manages backup integrity verification with user-friendly reporting.
    
    Responsibilities:
    - Periodic integrity checks using backup tool capabilities
    - Integrity status tracking and reporting
    - User-initiated verification support
    - Clear guidance for integrity issues
    
    Requirements addressed: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize integrity checker
        
        Args:
            config_dir: Directory for integrity check configuration and history
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "integrity"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.check_history_file = self.config_dir / "check_history.json"
        self.status_file = self.config_dir / "integrity_status.json"
        self.schedule_file = self.config_dir / "check_schedule.json"
        
        # Load existing data
        self.check_history: Dict[str, List[IntegrityCheckResult]] = self._load_check_history()
        self.repository_status: Dict[str, IntegrityStatus] = self._load_repository_status()
        self.check_schedule: Dict[str, Dict[str, Any]] = self._load_check_schedule()
        
        # Default check interval
        self.default_interval = CheckInterval.DAILY
    
    def _load_check_history(self) -> Dict[str, List[IntegrityCheckResult]]:
        """Load integrity check history from file"""
        try:
            if self.check_history_file.exists():
                with open(self.check_history_file, 'r') as f:
                    data = json.load(f)
                    return {
                        repo_id: [IntegrityCheckResult.from_dict(check) for check in checks]
                        for repo_id, checks in data.items()
                    }
        except Exception as e:
            logger.warning(f"Failed to load check history: {e}")
        return {}
    
    def _save_check_history(self):
        """Save integrity check history to file"""
        try:
            data = {
                repo_id: [check.to_dict() for check in checks]
                for repo_id, checks in self.check_history.items()
            }
            with open(self.check_history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save check history: {e}")
    
    def _load_repository_status(self) -> Dict[str, IntegrityStatus]:
        """Load repository integrity status from file"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    return {
                        repo_id: IntegrityStatus.from_dict(status)
                        for repo_id, status in data.items()
                    }
        except Exception as e:
            logger.warning(f"Failed to load repository status: {e}")
        return {}
    
    def _save_repository_status(self):
        """Save repository integrity status to file"""
        try:
            data = {
                repo_id: status.to_dict()
                for repo_id, status in self.repository_status.items()
            }
            with open(self.status_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save repository status: {e}")
    
    def _load_check_schedule(self) -> Dict[str, Dict[str, Any]]:
        """Load integrity check schedule from file"""
        try:
            if self.schedule_file.exists():
                with open(self.schedule_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load check schedule: {e}")
        return {}
    
    def _save_check_schedule(self):
        """Save integrity check schedule to file"""
        try:
            with open(self.schedule_file, 'w') as f:
                json.dump(self.check_schedule, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save check schedule: {e}")
    
    def schedule_integrity_check(self, repository_id: str, interval: CheckInterval) -> None:
        """
        Schedule periodic integrity checks for repository
        
        Args:
            repository_id: Repository to schedule checks for
            interval: Check interval (daily, weekly, etc.)
            
        Requirements: 5.1
        """
        logger.info(f"Scheduling {interval.value} integrity checks for repository {repository_id}")
        
        # Calculate next check time based on interval
        now = datetime.now()
        interval_days = {
            CheckInterval.DAILY: 1,
            CheckInterval.WEEKLY: 7,
            CheckInterval.BIWEEKLY: 14,
            CheckInterval.MONTHLY: 30
        }
        
        days = interval_days.get(interval, 1)
        next_check = now + timedelta(days=days)
        
        # Update schedule
        self.check_schedule[repository_id] = {
            'interval': interval.value,
            'next_check': next_check.isoformat(),
            'enabled': True
        }
        
        # Update repository status
        if repository_id not in self.repository_status:
            self.repository_status[repository_id] = IntegrityStatus(
                repository_id=repository_id,
                last_check=None,
                status=IntegrityLevel.UNKNOWN,
                issues_found=0,
                check_duration=None,
                next_scheduled_check=next_check,
                check_interval=interval
            )
        else:
            self.repository_status[repository_id].check_interval = interval
            self.repository_status[repository_id].next_scheduled_check = next_check
        
        self._save_check_schedule()
        self._save_repository_status()
        
        logger.info(f"Next integrity check scheduled for {next_check.isoformat()}")
    
    def run_integrity_check(self, repository, snapshot_id: Optional[str] = None) -> IntegrityCheckResult:
        """
        Run integrity check for specific repository
        
        Args:
            repository: Repository instance to verify
            snapshot_id: Specific snapshot to verify (optional)
            
        Returns:
            IntegrityCheckResult: Result of the integrity check
            
        Requirements: 5.1, 5.3, 5.4
        """
        check_id = f"check_{repository.id if hasattr(repository, 'id') else 'unknown'}_{int(datetime.now().timestamp())}"
        repository_id = repository.id if hasattr(repository, 'id') else str(repository._location)
        
        logger.info(f"Running integrity check for repository {repository_id}")
        start_time = datetime.now()
        
        issues = []
        snapshots_checked = 0
        data_verified_bytes = 0
        
        try:
            # Use repository's check method
            if snapshot_id:
                logger.info(f"Checking specific snapshot: {snapshot_id}")
                if hasattr(repository, 'check_snapshot'):
                    result = repository.check_snapshot(snapshot_id)
                    snapshots_checked = 1
                else:
                    result = repository.check()
                    snapshots_checked = 1
            else:
                logger.info("Checking entire repository")
                result = repository.check()
                
                # Try to get snapshot count
                if hasattr(repository, 'list_snapshots'):
                    try:
                        snapshots = repository.list_snapshots()
                        snapshots_checked = len(snapshots)
                    except Exception:
                        snapshots_checked = 0
            
            # Parse check result for issues
            result_lower = result.lower() if isinstance(result, str) else str(result).lower()
            
            if "error" in result_lower or "failed" in result_lower or "corrupt" in result_lower:
                # Extract issue details
                issue = IntegrityIssue(
                    issue_id=f"issue_{check_id}",
                    severity="high",
                    description="Integrity check detected errors in repository",
                    affected_snapshots=[snapshot_id] if snapshot_id else [],
                    detected_at=datetime.now(),
                    suggested_action="Review detailed error message and consider re-running backup",
                    metadata={'check_output': result[:500]}  # Truncate for storage
                )
                issues.append(issue)
                status = IntegrityLevel.ERROR
            elif "warning" in result_lower:
                issue = IntegrityIssue(
                    issue_id=f"issue_{check_id}",
                    severity="medium",
                    description="Integrity check found warnings",
                    affected_snapshots=[snapshot_id] if snapshot_id else [],
                    detected_at=datetime.now(),
                    suggested_action="Review warnings and monitor for recurring issues",
                    metadata={'check_output': result[:500]}
                )
                issues.append(issue)
                status = IntegrityLevel.WARNING
            else:
                status = IntegrityLevel.HEALTHY
                logger.info("Integrity check passed successfully")
            
            # Try to estimate data verified
            if hasattr(repository, 'get_repository_info'):
                try:
                    repo_info = repository.get_repository_info()
                    data_verified_bytes = repo_info.get('total_size', 0)
                except Exception:
                    pass
            
        except Exception as e:
            logger.error(f"Integrity check failed with exception: {e}")
            issue = IntegrityIssue(
                issue_id=f"issue_{check_id}",
                severity="critical",
                description=f"Integrity check failed: {str(e)}",
                affected_snapshots=[snapshot_id] if snapshot_id else [],
                detected_at=datetime.now(),
                suggested_action="Check repository connectivity and try again",
                metadata={'error': str(e)}
            )
            issues.append(issue)
            status = IntegrityLevel.ERROR
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Create check result
        check_result = IntegrityCheckResult(
            check_id=check_id,
            repository_id=repository_id,
            check_time=start_time,
            status=status,
            duration=duration,
            issues_found=issues,
            snapshots_checked=snapshots_checked,
            data_verified_bytes=data_verified_bytes,
            metadata={
                'snapshot_id': snapshot_id,
                'check_type': 'snapshot' if snapshot_id else 'full'
            }
        )
        
        # Update history
        if repository_id not in self.check_history:
            self.check_history[repository_id] = []
        self.check_history[repository_id].append(check_result)
        
        # Keep only last 30 checks per repository
        if len(self.check_history[repository_id]) > 30:
            self.check_history[repository_id] = self.check_history[repository_id][-30:]
        
        # Update repository status
        next_check = self._calculate_next_check(repository_id)
        self.repository_status[repository_id] = IntegrityStatus(
            repository_id=repository_id,
            last_check=start_time,
            status=status,
            issues_found=len(issues),
            check_duration=duration,
            next_scheduled_check=next_check,
            check_interval=self.repository_status.get(repository_id, IntegrityStatus(
                repository_id=repository_id,
                last_check=None,
                status=IntegrityLevel.UNKNOWN,
                issues_found=0,
                check_duration=None,
                next_scheduled_check=None,
                check_interval=self.default_interval
            )).check_interval
        )
        
        self._save_check_history()
        self._save_repository_status()
        
        logger.info(f"Integrity check completed: {status.value}, {len(issues)} issues found")
        
        return check_result
    
    def _calculate_next_check(self, repository_id: str) -> Optional[datetime]:
        """Calculate next scheduled check time for repository"""
        if repository_id not in self.check_schedule:
            return None
        
        schedule = self.check_schedule[repository_id]
        if not schedule.get('enabled', True):
            return None
        
        interval = CheckInterval(schedule['interval'])
        interval_days = {
            CheckInterval.DAILY: 1,
            CheckInterval.WEEKLY: 7,
            CheckInterval.BIWEEKLY: 14,
            CheckInterval.MONTHLY: 30
        }
        
        days = interval_days.get(interval, 1)
        return datetime.now() + timedelta(days=days)
    
    def get_integrity_status(self, repository_id: str) -> IntegrityStatus:
        """
        Get current integrity status for repository
        
        Args:
            repository_id: Repository to get status for
            
        Returns:
            IntegrityStatus: Current integrity status
            
        Requirements: 5.3
        """
        if repository_id in self.repository_status:
            return self.repository_status[repository_id]
        
        # Return default status if not found
        return IntegrityStatus(
            repository_id=repository_id,
            last_check=None,
            status=IntegrityLevel.UNKNOWN,
            issues_found=0,
            check_duration=None,
            next_scheduled_check=None,
            check_interval=self.default_interval
        )
    
    def get_recent_checks(self, repository_id: str, limit: int = 10) -> List[IntegrityCheckResult]:
        """
        Get recent integrity check results for repository
        
        Args:
            repository_id: Repository to get checks for
            limit: Maximum number of checks to return
            
        Returns:
            List of recent integrity check results
        """
        if repository_id not in self.check_history:
            return []
        
        return self.check_history[repository_id][-limit:]
    
    def get_remediation_guidance(self, issues: List[IntegrityIssue]) -> RemediationGuide:
        """
        Get user-friendly guidance for integrity issues
        
        Args:
            issues: List of integrity issues
            
        Returns:
            RemediationGuide: User-friendly remediation guidance
            
        Requirements: 5.2, 5.5
        """
        if not issues:
            return RemediationGuide(
                issue_summary="No integrity issues detected",
                severity="none",
                affected_backups=[],
                recommended_actions=["Continue regular backup schedule"],
                detailed_steps=["No action required"],
                additional_resources=[],
                estimated_time="N/A",
                requires_technical_support=False
            )
        
        # Determine overall severity
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        max_severity = max(issues, key=lambda i: severity_order.get(i.severity, 0)).severity
        
        # Collect affected snapshots
        affected_backups = []
        for issue in issues:
            affected_backups.extend(issue.affected_snapshots)
        affected_backups = list(set(affected_backups))  # Remove duplicates
        
        # Generate recommendations based on severity
        if max_severity == "critical":
            recommended_actions = [
                "Stop all backup operations immediately",
                "Verify repository connectivity and credentials",
                "Check available disk space on backup storage",
                "Review system logs for additional error details",
                "Contact technical support if issue persists"
            ]
            detailed_steps = [
                "1. Open TimeLocker and navigate to the affected repository",
                "2. Click 'Verify Repository' to run a manual integrity check",
                "3. If errors persist, check your backup storage is accessible",
                "4. Ensure you have sufficient disk space (at least 10% free)",
                "5. Try running a new backup to see if the issue is resolved",
                "6. If problems continue, export logs and contact support"
            ]
            estimated_time = "30-60 minutes"
            requires_technical_support = True
        elif max_severity == "high":
            recommended_actions = [
                "Run a manual integrity check to confirm the issue",
                "Review the affected backups and consider re-running them",
                "Check repository connectivity and storage space",
                "Monitor for recurring issues"
            ]
            detailed_steps = [
                "1. Navigate to the affected repository in TimeLocker",
                "2. Click 'Run Integrity Check' to verify the issue",
                "3. If confirmed, select 'Re-run Backup' for affected data",
                "4. Monitor the backup progress for any errors",
                "5. Verify the new backup completes successfully"
            ]
            estimated_time = "15-30 minutes"
            requires_technical_support = False
        else:
            recommended_actions = [
                "Review the warnings in the integrity check report",
                "Monitor for recurring issues in future backups",
                "Consider running a manual backup if concerned"
            ]
            detailed_steps = [
                "1. Review the integrity check report details",
                "2. Note any patterns or recurring warnings",
                "3. Continue with regular backup schedule",
                "4. Run manual integrity checks if concerned"
            ]
            estimated_time = "5-10 minutes"
            requires_technical_support = False
        
        # Additional resources
        additional_resources = [
            "TimeLocker User Guide: Troubleshooting Integrity Issues",
            "Knowledge Base: Understanding Backup Integrity",
            "Support Forum: Common Integrity Check Questions"
        ]
        
        # Create summary
        issue_count = len(issues)
        issue_summary = f"Found {issue_count} integrity issue{'s' if issue_count != 1 else ''} "
        issue_summary += f"with {max_severity} severity"
        if affected_backups:
            issue_summary += f" affecting {len(affected_backups)} backup{'s' if len(affected_backups) != 1 else ''}"
        
        return RemediationGuide(
            issue_summary=issue_summary,
            severity=max_severity,
            affected_backups=affected_backups,
            recommended_actions=recommended_actions,
            detailed_steps=detailed_steps,
            additional_resources=additional_resources,
            estimated_time=estimated_time,
            requires_technical_support=requires_technical_support
        )
    
    def get_repositories_needing_check(self) -> List[str]:
        """
        Get list of repositories that need integrity checks
        
        Returns:
            List of repository IDs that need checking
        """
        now = datetime.now()
        repositories_needing_check = []
        
        for repo_id, schedule in self.check_schedule.items():
            if not schedule.get('enabled', True):
                continue
            
            next_check_str = schedule.get('next_check')
            if next_check_str:
                next_check = datetime.fromisoformat(next_check_str)
                if next_check <= now:
                    repositories_needing_check.append(repo_id)
        
        return repositories_needing_check
