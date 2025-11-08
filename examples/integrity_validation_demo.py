#!/usr/bin/env python3
"""
Integrity Validation System Demo

This example demonstrates the integrity validation capabilities for backup operations,
showing how the system leverages native tool features and provides wrapper-based
validation for tools without native support.

Requirements demonstrated: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from TimeLocker.services.integrity_validation_service import (
    IntegrityValidationService,
    ValidationStatus,
    ValidationMethod
)
from TimeLocker.services.tool_manager import ToolManager, Feature
from TimeLocker.services.wrapper_registry import WrapperRegistry
from TimeLocker.interfaces.data_models import (
    BackupJob,
    BackupJobConfig,
    BackupResult,
    BackupStatus,
    ExecutionMode,
    RetryConfig,
    NotificationConfig,
    ToolConfiguration,
    ExecutionContext
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_validation_result(result):
    """Print validation result details"""
    print(f"Status: {result.status.value}")
    print(f"Method: {result.method.value}")
    print(f"Validation Time: {result.validation_time:.2f}s")
    print(f"Files Validated: {result.files_validated}")
    print(f"Bytes Validated: {result.bytes_validated:,}")
    print(f"Issues Found: {len(result.issues)}")
    
    if result.issues:
        print("\nIssues:")
        for i, issue in enumerate(result.issues, 1):
            print(f"  {i}. [{issue.severity.upper()}] {issue.description}")
            if issue.suggested_action:
                print(f"     Action: {issue.suggested_action}")
    
    if result.metadata:
        print("\nMetadata:")
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")


def demo_tool_capabilities():
    """Demonstrate tool capability detection for integrity validation"""
    print_section("Tool Capability Detection")
    
    tool_manager = ToolManager()
    validation_service = IntegrityValidationService(tool_manager=tool_manager)
    
    # Check capabilities for different tools
    tools = ['restic', 'borg', 'duplicity']
    
    for tool in tools:
        print(f"\n{tool.upper()} Capabilities:")
        print("-" * 40)
        
        try:
            capabilities = tool_manager.get_tool_capabilities(tool)
            
            # Check integrity-related features
            has_integrity = capabilities.has_feature(Feature.INTEGRITY_VERIFICATION)
            has_checksum = capabilities.has_feature(Feature.CHECKSUM_VALIDATION)
            has_repo_verify = capabilities.has_feature(Feature.REPOSITORY_VERIFICATION)
            
            print(f"Integrity Verification: {'✓' if has_integrity else '✗'} "
                  f"({'native' if capabilities.is_native_feature(Feature.INTEGRITY_VERIFICATION) else 'wrapper'})")
            print(f"Checksum Validation: {'✓' if has_checksum else '✗'}")
            print(f"Repository Verification: {'✓' if has_repo_verify else '✗'}")
            
            # Get recommendations
            recommendations = validation_service.get_validation_recommendations(tool, capabilities)
            if recommendations:
                print("\nRecommendations:")
                for rec in recommendations:
                    print(f"  • {rec}")
                    
        except Exception as e:
            print(f"Error detecting capabilities: {e}")


def demo_native_validation():
    """Demonstrate native tool validation (Restic)"""
    print_section("Native Tool Validation (Restic)")
    
    validation_service = IntegrityValidationService()
    
    # Create a mock backup job for Restic
    job_config = BackupJobConfig(
        job_id="demo-restic-001",
        policy_id="policy-001",
        repository_id="demo-repo",
        data_selection_id="selection-001",
        tool_type="restic",
        execution_mode=ExecutionMode.ON_DEMAND,
        retry_config=RetryConfig(),
        notification_config=NotificationConfig(),
        tags=["demo", "restic"],
        priority=5,
        dry_run=False
    )
    
    backup_job = BackupJob(
        config=job_config,
        source_paths=["/tmp/demo/data"],
        exclude_patterns=["*.tmp", "*.log"],
        include_patterns=["*.txt", "*.pdf"],
        tool_configuration=ToolConfiguration(
            tool_type="restic",
            parallel_operations=4,
            encryption_enabled=True,
            integrity_check_enabled=True
        ),
        execution_context=ExecutionContext(
            start_time=datetime.now().timestamp(),
            attempt_number=1
        )
    )
    
    # Create a successful backup result
    backup_result = BackupResult(
        status=BackupStatus.COMPLETED,
        repository_name="demo-repo",
        target_names=["demo-target"],
        start_time=datetime.now().timestamp(),
        end_time=datetime.now().timestamp(),
        snapshot_id="abc123def456",
        files_processed=1250,
        bytes_processed=524288000,  # ~500MB
        errors=[],
        warnings=[],
        metadata={'job_id': job_config.job_id}
    )
    
    print("Backup Job Configuration:")
    print(f"  Tool: {job_config.tool_type}")
    print(f"  Job ID: {job_config.job_id}")
    print(f"  Files Processed: {backup_result.files_processed}")
    print(f"  Bytes Processed: {backup_result.bytes_processed:,}")
    
    print("\nPerforming integrity validation...")
    validation_result = validation_service.validate_backup_integrity(backup_job, backup_result)
    
    print("\nValidation Results:")
    print_validation_result(validation_result)
    
    # Generate validation report
    print("\nValidation Report:")
    report = validation_service.generate_validation_report(validation_result)
    print(f"  Summary: {report['summary']}")
    print(f"  Statistics: {report['statistics']}")


def demo_wrapper_validation():
    """Demonstrate wrapper-based validation for tools without native support"""
    print_section("Wrapper-Based Validation")
    
    validation_service = IntegrityValidationService()
    
    # Create a mock backup job for a tool with limited native validation
    job_config = BackupJobConfig(
        job_id="demo-wrapper-001",
        policy_id="policy-002",
        repository_id="demo-repo-2",
        data_selection_id="selection-002",
        tool_type="duplicity",
        execution_mode=ExecutionMode.ON_DEMAND,
        retry_config=RetryConfig(),
        notification_config=NotificationConfig(),
        tags=["demo", "wrapper"],
        priority=5,
        dry_run=False
    )
    
    backup_job = BackupJob(
        config=job_config,
        source_paths=["/tmp/demo/documents"],
        exclude_patterns=["*.bak"],
        include_patterns=[],
        tool_configuration=ToolConfiguration(
            tool_type="duplicity",
            parallel_operations=1,
            encryption_enabled=True,
            integrity_check_enabled=False  # Not natively supported
        ),
        execution_context=ExecutionContext(
            start_time=datetime.now().timestamp(),
            attempt_number=1
        )
    )
    
    # Create a backup result with some warnings
    backup_result = BackupResult(
        status=BackupStatus.COMPLETED,
        repository_name="demo-repo-2",
        target_names=["documents"],
        start_time=datetime.now().timestamp(),
        end_time=datetime.now().timestamp(),
        snapshot_id="xyz789abc123",
        files_processed=850,
        bytes_processed=314572800,  # ~300MB
        errors=[],
        warnings=["Some files were skipped due to permissions"],
        metadata={'job_id': job_config.job_id}
    )
    
    print("Backup Job Configuration:")
    print(f"  Tool: {job_config.tool_type}")
    print(f"  Job ID: {job_config.job_id}")
    print(f"  Files Processed: {backup_result.files_processed}")
    print(f"  Warnings: {len(backup_result.warnings)}")
    
    print("\nPerforming wrapper-based validation...")
    validation_result = validation_service.validate_backup_integrity(backup_job, backup_result)
    
    print("\nValidation Results:")
    print_validation_result(validation_result)


def demo_validation_failure():
    """Demonstrate validation failure handling"""
    print_section("Validation Failure Handling")
    
    validation_service = IntegrityValidationService()
    
    # Create a backup job
    job_config = BackupJobConfig(
        job_id="demo-failure-001",
        policy_id="policy-003",
        repository_id="demo-repo-3",
        data_selection_id="selection-003",
        tool_type="restic",
        execution_mode=ExecutionMode.ON_DEMAND,
        retry_config=RetryConfig(),
        notification_config=NotificationConfig(),
        tags=["demo", "failure"],
        priority=5,
        dry_run=False
    )
    
    # Add expected file count to job config metadata
    job_config.metadata = {'expected_file_count': 1000}
    
    backup_job = BackupJob(
        config=job_config,
        source_paths=["/tmp/demo/critical"],
        exclude_patterns=[],
        include_patterns=[],
        tool_configuration=ToolConfiguration(
            tool_type="restic",
            parallel_operations=4,
            encryption_enabled=True,
            integrity_check_enabled=True
        ),
        execution_context=ExecutionContext(
            start_time=datetime.now().timestamp(),
            attempt_number=1
        )
    )
    
    # Create a backup result with errors
    backup_result = BackupResult(
        status=BackupStatus.COMPLETED,
        repository_name="demo-repo-3",
        target_names=["critical-data"],
        start_time=datetime.now().timestamp(),
        end_time=datetime.now().timestamp(),
        snapshot_id="failed123",
        files_processed=650,  # Less than expected
        bytes_processed=209715200,  # ~200MB
        errors=["Checksum mismatch detected in 5 files"],
        warnings=["Permission denied for 10 files"],
        metadata={'job_id': job_config.job_id}
    )
    
    print("Backup Job Configuration:")
    print(f"  Tool: {job_config.tool_type}")
    print(f"  Job ID: {job_config.job_id}")
    print(f"  Expected Files: 1000")
    print(f"  Actual Files: {backup_result.files_processed}")
    print(f"  Errors: {len(backup_result.errors)}")
    
    print("\nPerforming integrity validation...")
    validation_result = validation_service.validate_backup_integrity(backup_job, backup_result)
    
    print("\nValidation Results:")
    print_validation_result(validation_result)
    
    # Integrate with backup result
    print("\nIntegrating validation with backup result...")
    updated_result = validation_service.integrate_validation_with_backup_result(
        backup_result,
        validation_result
    )
    
    print(f"Updated Backup Status: {updated_result.status.value}")
    print(f"Integrity Validated: {updated_result.metadata.get('integrity_validated', False)}")
    print(f"Validation Metadata: {updated_result.metadata.get('integrity_validation', {})}")


def demo_validation_report():
    """Demonstrate validation report generation"""
    print_section("Validation Report Generation")
    
    validation_service = IntegrityValidationService()
    
    # Create a sample validation result
    from TimeLocker.services.integrity_validation_service import IntegrityValidationResult, ValidationIssue
    
    validation_result = IntegrityValidationResult(
        status=ValidationStatus.PARTIAL,
        method=ValidationMethod.NATIVE_TOOL,
        validation_time=12.5,
        files_validated=2500,
        bytes_validated=1073741824,  # 1GB
        checksum_mismatches=3,
        missing_files=2,
        corrupted_files=1
    )
    
    # Add some issues
    validation_result.add_issue(
        severity="high",
        description="Checksum mismatch detected in critical files",
        affected_files=["/data/file1.dat", "/data/file2.dat", "/data/file3.dat"],
        suggested_action="Verify source files and retry backup"
    )
    
    validation_result.add_issue(
        severity="medium",
        description="Some files were not accessible during validation",
        affected_files=["/data/locked1.dat", "/data/locked2.dat"],
        suggested_action="Check file permissions and locks"
    )
    
    validation_result.add_issue(
        severity="low",
        description="Validation took longer than expected",
        suggested_action="Consider optimizing backup tool configuration"
    )
    
    # Generate report
    report = validation_service.generate_validation_report(validation_result)
    
    print("Validation Report:")
    print(f"\nSummary:")
    for key, value in report['summary'].items():
        print(f"  {key}: {value}")
    
    print(f"\nStatistics:")
    for key, value in report['statistics'].items():
        print(f"  {key}: {value}")
    
    print(f"\nIssues ({len(report['issues'])}):")
    for i, issue in enumerate(report['issues'], 1):
        print(f"\n  Issue {i}:")
        print(f"    Severity: {issue['severity']}")
        print(f"    Description: {issue['description']}")
        print(f"    Affected Files: {issue['affected_files_count']}")
        if issue['affected_files_sample']:
            print(f"    Sample Files: {', '.join(issue['affected_files_sample'])}")
        if issue['suggested_action']:
            print(f"    Suggested Action: {issue['suggested_action']}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 80)
    print("  INTEGRITY VALIDATION SYSTEM DEMONSTRATION")
    print("=" * 80)
    
    try:
        # Demo 1: Tool capabilities
        demo_tool_capabilities()
        
        # Demo 2: Native validation
        demo_native_validation()
        
        # Demo 3: Wrapper validation
        demo_wrapper_validation()
        
        # Demo 4: Validation failure
        demo_validation_failure()
        
        # Demo 5: Validation report
        demo_validation_report()
        
        print_section("Demo Complete")
        print("All integrity validation demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  ✓ Native tool integrity validation (Restic, Borg)")
        print("  ✓ Wrapper-based validation for unsupported tools")
        print("  ✓ Comprehensive validation result reporting")
        print("  ✓ Integration with backup completion workflow")
        print("  ✓ Validation failure handling and error reporting")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
