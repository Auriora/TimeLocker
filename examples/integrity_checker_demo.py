#!/usr/bin/env python3
"""
Demonstration of the Integrity Checker component for monitoring.

This script demonstrates:
1. Scheduling periodic integrity checks
2. Running manual integrity checks
3. Getting integrity status
4. Receiving remediation guidance for issues
5. Integration with monitoring service

Requirements addressed: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.monitoring import (
    IntegrityChecker,
    IntegrityLevel,
    IntegrityStatus,
    CheckInterval,
    MonitoringService
)


class MockRepository:
    """Mock repository for demonstration"""
    
    def __init__(self, repo_id: str, has_issues: bool = False):
        self.id = repo_id
        self._location = f"/tmp/test-repo-{repo_id}"
        self.has_issues = has_issues
    
    def check(self) -> str:
        """Simulate repository check"""
        if self.has_issues:
            return "Error: Repository integrity check failed - corrupted data detected"
        return "Repository check passed successfully"
    
    def check_snapshot(self, snapshot_id: str) -> str:
        """Simulate snapshot check"""
        if self.has_issues:
            return f"Error: Snapshot {snapshot_id} integrity check failed"
        return f"Snapshot {snapshot_id} check passed"
    
    def list_snapshots(self):
        """Simulate listing snapshots"""
        return [
            {'id': 'snap1', 'time': datetime.now()},
            {'id': 'snap2', 'time': datetime.now() - timedelta(days=1)},
            {'id': 'snap3', 'time': datetime.now() - timedelta(days=2)}
        ]
    
    def get_repository_info(self):
        """Simulate getting repository info"""
        return {
            'id': self.id,
            'total_size': 1024 * 1024 * 1024,  # 1GB
            'version': '2'
        }


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def demo_integrity_checker():
    """Demonstrate IntegrityChecker functionality"""
    
    print_section("Integrity Checker Demo")
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        
        # Initialize integrity checker
        print("1. Initializing IntegrityChecker...")
        checker = IntegrityChecker(config_dir=config_dir)
        print("   ✓ IntegrityChecker initialized")
        
        # Create mock repositories
        healthy_repo = MockRepository("healthy-repo", has_issues=False)
        problematic_repo = MockRepository("problematic-repo", has_issues=True)
        
        # Demo 1: Schedule periodic integrity checks
        print_section("Demo 1: Scheduling Periodic Integrity Checks")
        
        print("Scheduling daily integrity checks for healthy repository...")
        checker.schedule_integrity_check(healthy_repo.id, CheckInterval.DAILY)
        print(f"   ✓ Scheduled daily checks for {healthy_repo.id}")
        
        print("\nScheduling weekly integrity checks for problematic repository...")
        checker.schedule_integrity_check(problematic_repo.id, CheckInterval.WEEKLY)
        print(f"   ✓ Scheduled weekly checks for {problematic_repo.id}")
        
        # Demo 2: Run manual integrity check on healthy repository
        print_section("Demo 2: Running Integrity Check on Healthy Repository")
        
        print(f"Running integrity check on {healthy_repo.id}...")
        result = checker.run_integrity_check(healthy_repo)
        
        print(f"\nCheck Results:")
        print(f"   Check ID: {result.check_id}")
        print(f"   Status: {result.status.value}")
        print(f"   Duration: {result.duration.total_seconds():.2f} seconds")
        print(f"   Snapshots Checked: {result.snapshots_checked}")
        print(f"   Issues Found: {len(result.issues_found)}")
        print(f"   Data Verified: {result.data_verified_bytes / (1024*1024):.2f} MB")
        
        # Demo 3: Run integrity check on problematic repository
        print_section("Demo 3: Running Integrity Check on Problematic Repository")
        
        print(f"Running integrity check on {problematic_repo.id}...")
        result = checker.run_integrity_check(problematic_repo)
        
        print(f"\nCheck Results:")
        print(f"   Check ID: {result.check_id}")
        print(f"   Status: {result.status.value}")
        print(f"   Duration: {result.duration.total_seconds():.2f} seconds")
        print(f"   Snapshots Checked: {result.snapshots_checked}")
        print(f"   Issues Found: {len(result.issues_found)}")
        
        if result.issues_found:
            print(f"\n   Issues Detected:")
            for issue in result.issues_found:
                print(f"      - Severity: {issue.severity}")
                print(f"        Description: {issue.description}")
                print(f"        Suggested Action: {issue.suggested_action}")
        
        # Demo 4: Get integrity status
        print_section("Demo 4: Getting Integrity Status")
        
        for repo in [healthy_repo, problematic_repo]:
            status = checker.get_integrity_status(repo.id)
            print(f"\nRepository: {repo.id}")
            print(f"   Status: {status.status.value}")
            print(f"   Last Check: {status.last_check.strftime('%Y-%m-%d %H:%M:%S') if status.last_check else 'Never'}")
            print(f"   Issues Found: {status.issues_found}")
            print(f"   Check Interval: {status.check_interval.value}")
            if status.next_scheduled_check:
                print(f"   Next Check: {status.next_scheduled_check.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Demo 5: Get remediation guidance
        print_section("Demo 5: Getting Remediation Guidance")
        
        print(f"Getting remediation guidance for {problematic_repo.id}...")
        recent_checks = checker.get_recent_checks(problematic_repo.id, limit=1)
        
        if recent_checks and recent_checks[0].issues_found:
            guidance = checker.get_remediation_guidance(recent_checks[0].issues_found)
            
            print(f"\nRemediation Guidance:")
            print(f"   Summary: {guidance.issue_summary}")
            print(f"   Severity: {guidance.severity}")
            print(f"   Estimated Time: {guidance.estimated_time}")
            print(f"   Requires Technical Support: {guidance.requires_technical_support}")
            
            print(f"\n   Recommended Actions:")
            for i, action in enumerate(guidance.recommended_actions, 1):
                print(f"      {i}. {action}")
            
            print(f"\n   Detailed Steps:")
            for step in guidance.detailed_steps:
                print(f"      {step}")
            
            if guidance.additional_resources:
                print(f"\n   Additional Resources:")
                for resource in guidance.additional_resources:
                    print(f"      - {resource}")
        
        # Demo 6: Check for repositories needing checks
        print_section("Demo 6: Checking for Repositories Needing Integrity Checks")
        
        # Manually set next check to past to simulate needing check
        checker.check_schedule[healthy_repo.id]['next_check'] = (datetime.now() - timedelta(hours=1)).isoformat()
        checker._save_check_schedule()
        
        repos_needing_check = checker.get_repositories_needing_check()
        print(f"Repositories needing integrity check: {len(repos_needing_check)}")
        for repo_id in repos_needing_check:
            print(f"   - {repo_id}")
        
        # Demo 7: Check specific snapshot
        print_section("Demo 7: Checking Specific Snapshot")
        
        print(f"Running integrity check on specific snapshot...")
        result = checker.run_integrity_check(healthy_repo, snapshot_id="snap1")
        
        print(f"\nSnapshot Check Results:")
        print(f"   Status: {result.status.value}")
        print(f"   Snapshot ID: {result.metadata.get('snapshot_id')}")
        print(f"   Check Type: {result.metadata.get('check_type')}")
        print(f"   Issues Found: {len(result.issues_found)}")


def demo_monitoring_service_integration():
    """Demonstrate MonitoringService integration with IntegrityChecker"""
    
    print_section("MonitoringService Integration Demo")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        
        # Initialize monitoring service
        print("1. Initializing MonitoringService...")
        monitoring = MonitoringService(config_dir=config_dir)
        print("   ✓ MonitoringService initialized with IntegrityChecker")
        
        # Create mock repository
        repo = MockRepository("test-repo", has_issues=True)
        
        # Schedule integrity check through monitoring service
        print_section("Scheduling Integrity Check via MonitoringService")
        
        print(f"Scheduling daily integrity checks for {repo.id}...")
        monitoring.schedule_integrity_check(repo.id, CheckInterval.DAILY)
        print("   ✓ Integrity check scheduled")
        
        # Run integrity check through monitoring service
        print_section("Running Integrity Check via MonitoringService")
        
        print(f"Running integrity check on {repo.id}...")
        result = monitoring.run_integrity_check(repo)
        
        print(f"\nCheck Results:")
        print(f"   Status: {result.status.value}")
        print(f"   Issues Found: {len(result.issues_found)}")
        print(f"   Duration: {result.duration.total_seconds():.2f} seconds")
        
        # Get integrity status through monitoring service
        print_section("Getting Integrity Status via MonitoringService")
        
        status = monitoring.get_integrity_status(repo.id)
        print(f"\nIntegrity Status for {repo.id}:")
        print(f"   Status: {status.status.value}")
        print(f"   Last Check: {status.last_check.strftime('%Y-%m-%d %H:%M:%S') if status.last_check else 'Never'}")
        print(f"   Issues Found: {status.issues_found}")
        
        # Get remediation guidance through monitoring service
        if status.issues_found > 0:
            print_section("Getting Remediation Guidance via MonitoringService")
            
            guidance = monitoring.get_remediation_guidance(repo.id)
            if guidance:
                print(f"\nRemediation Guidance:")
                print(f"   Summary: {guidance.issue_summary}")
                print(f"   Severity: {guidance.severity}")
                print(f"   Estimated Time: {guidance.estimated_time}")
                
                print(f"\n   Recommended Actions:")
                for i, action in enumerate(guidance.recommended_actions, 1):
                    print(f"      {i}. {action}")


def main():
    """Main demo function"""
    print("\n" + "=" * 80)
    print("  TimeLocker Integrity Checker Demonstration")
    print("  Requirements: 5.1, 5.2, 5.3, 5.4, 5.5")
    print("=" * 80)
    
    try:
        # Run IntegrityChecker demo
        demo_integrity_checker()
        
        # Run MonitoringService integration demo
        demo_monitoring_service_integration()
        
        print_section("Demo Complete")
        print("All integrity checking features demonstrated successfully!")
        print("\nKey Features Demonstrated:")
        print("   ✓ Periodic integrity check scheduling (Requirement 5.1)")
        print("   ✓ Manual integrity verification (Requirement 5.4)")
        print("   ✓ Integrity status tracking (Requirement 5.3)")
        print("   ✓ User-friendly remediation guidance (Requirement 5.2, 5.5)")
        print("   ✓ Integration with MonitoringService")
        print("   ✓ Desktop notification support for integrity issues")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
