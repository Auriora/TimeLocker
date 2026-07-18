#!/usr/bin/env python3
"""
Recovery Operations Service Integration Demo

This example demonstrates how the RecoveryOrchestrator integrates with
existing TimeLocker services including Repository Management, Data Selection,
and Security Services.

Copyright © Bruce Cherrington
Licensed under GPL v3
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_repository_integration():
    """
    Demonstrate Repository Management integration with recovery operations.
    
    This shows how the RecoveryOrchestrator validates repository accessibility,
    checks for conflicts, and validates authentication before recovery.
    """
    print("\n" + "=" * 80)
    print("DEMO: Repository Management Integration")
    print("=" * 80 + "\n")
    
    from TimeLocker.backup_repository import BackupRepository
    from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
    from TimeLocker.services.repository_service import RepositoryService
    from TimeLocker.services.validation_service import ValidationService
    from TimeLocker.utils.performance_utils import PerformanceModule
    from TimeLocker.interfaces.recovery_models import RecoveryOptions
    
    # Create repository
    repo_path = Path("/tmp/demo_recovery_repo")
    repo_path.mkdir(parents=True, exist_ok=True)
    
    repository = BackupRepository(
        location=str(repo_path),
        password="demo_password_123"
    )
    
    # Initialize repository if needed
    if not repository.is_repository_initialized():
        print("Initializing repository...")
        repository.initialize_repository()
        print("✓ Repository initialized\n")
    
    # Create repository service
    validation_service = ValidationService()
    performance_module = PerformanceModule()
    repository_service = RepositoryService(
        validation_service=validation_service,
        performance_module=performance_module
    )
    
    # Create recovery orchestrator with repository service integration
    orchestrator = RecoveryOrchestrator(
        repository=repository,
        repository_service=repository_service
    )
    
    print("Repository Integration Features:")
    print("-" * 40)
    print("1. Repository Accessibility Validation")
    print("   - Checks if repository is initialized")
    print("   - Validates repository health")
    print("   - Ensures repository is ready for recovery\n")
    
    print("2. Conflict Detection")
    print("   - Checks for repository locks")
    print("   - Validates repository mode (read-only, locked, etc.)")
    print("   - Prevents conflicts with ongoing operations\n")
    
    print("3. Authentication Validation")
    print("   - Verifies repository credentials")
    print("   - Audits repository access")
    print("   - Ensures proper authorization\n")
    
    # Demonstrate validation
    try:
        print("Validating repository accessibility...")
        orchestrator._validate_repository_accessibility()
        print("✓ Repository is accessible and ready\n")
    except Exception as e:
        print(f"✗ Repository validation failed: {e}\n")
    
    # Check for conflicts
    try:
        print("Checking for repository conflicts...")
        orchestrator._check_repository_conflicts('full')
        print("✓ No conflicts detected\n")
    except Exception as e:
        print(f"✗ Conflict detected: {e}\n")
    
    # Validate authentication
    try:
        print("Validating repository authentication...")
        orchestrator._validate_repository_authentication()
        print("✓ Authentication validated\n")
    except Exception as e:
        print(f"✗ Authentication failed: {e}\n")
    
    print("Repository integration ensures safe and reliable recovery operations!")


async def demo_selection_integration():
    """
    Demonstrate Data Selection system integration with recovery operations.
    
    This shows how the RecoveryOrchestrator applies selection templates,
    validates selection criteria, and creates recovery-specific selections.
    """
    print("\n" + "=" * 80)
    print("DEMO: Data Selection System Integration")
    print("=" * 80 + "\n")
    
    from TimeLocker.backup_repository import BackupRepository
    from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
    from TimeLocker.selection_manager import SelectionManager
    from TimeLocker.interfaces.recovery_models import SelectionCriteria
    from TimeLocker.selection_models import (
        SelectionConfig,
        PatternRule,
        PatternSyntax,
        PathComponent,
        PrecedenceConfig
    )
    
    # Create repository
    repo_path = Path("/tmp/demo_selection_repo")
    repo_path.mkdir(parents=True, exist_ok=True)
    
    repository = BackupRepository(
        location=str(repo_path),
        password="demo_password_123"
    )
    
    # Initialize repository if needed
    if not repository.is_repository_initialized():
        repository.initialize_repository()
    
    # Create selection manager
    selection_manager = SelectionManager()
    
    # Create a selection template
    template_config = SelectionConfig(
        name="documents_template",
        include_patterns=[
            PatternRule(
                pattern="*.pdf",
                syntax=PatternSyntax.GLOB,
                case_sensitive=False,
                applies_to=PathComponent.FILENAME
            ),
            PatternRule(
                pattern="*.docx",
                syntax=PatternSyntax.GLOB,
                case_sensitive=False,
                applies_to=PathComponent.FILENAME
            )
        ],
        exclude_patterns=[
            PatternRule(
                pattern="**/temp/**",
                syntax=PatternSyntax.GLOB,
                case_sensitive=False,
                applies_to=PathComponent.FULL_PATH
            )
        ],
        precedence_config=PrecedenceConfig()
    )
    
    # Save template
    template = selection_manager.template_manager.create_template(
        name="documents_template",
        description="Template for document recovery",
        config=template_config
    )
    
    print("Selection Integration Features:")
    print("-" * 40)
    print("1. Template Application")
    print("   - Retrieves selection templates by ID")
    print("   - Merges template patterns with criteria")
    print("   - Applies templates during recovery\n")
    
    print("2. Criteria Validation")
    print("   - Validates selection patterns")
    print("   - Checks pattern syntax")
    print("   - Ensures criteria compatibility\n")
    
    print("3. Recovery-Specific Modifications")
    print("   - Creates recovery-specific selections")
    print("   - Allows modifications without affecting templates")
    print("   - Optimizes for recovery operations\n")
    
    # Create recovery orchestrator with selection manager
    orchestrator = RecoveryOrchestrator(
        repository=repository,
        selection_manager=selection_manager
    )
    
    # Create selection criteria with template
    selection_criteria = SelectionCriteria(
        include_patterns=["*.txt"],
        exclude_patterns=[],
        selection_template_id=template.template_id
    )
    
    print(f"Original criteria: {len(selection_criteria.include_patterns)} include patterns")
    print(f"Template: {template.name} with {len(template_config.include_patterns)} patterns\n")
    
    # Apply template
    try:
        print("Applying selection template...")
        merged_criteria = await orchestrator._apply_selection_template(selection_criteria)
        print(f"✓ Template applied successfully")
        print(f"  Merged criteria: {len(merged_criteria.include_patterns)} include patterns")
        print(f"  Patterns: {', '.join(merged_criteria.include_patterns)}\n")
    except Exception as e:
        print(f"✗ Template application failed: {e}\n")
    
    # Validate criteria
    try:
        print("Validating selection criteria...")
        await orchestrator._validate_selection_criteria(merged_criteria, "test_snapshot")
        print("✓ Selection criteria validated\n")
    except Exception as e:
        print(f"✗ Validation failed: {e}\n")
    
    print("Selection integration enables flexible and validated file recovery!")


def demo_security_integration():
    """
    Demonstrate Security Services integration with recovery operations.
    
    This shows how the RecoveryOrchestrator audits operations, validates
    encryption keys, and checks access control.
    """
    print("\n" + "=" * 80)
    print("DEMO: Security Services Integration")
    print("=" * 80 + "\n")
    
    from TimeLocker.backup_repository import BackupRepository
    from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
    from TimeLocker.security.security_service import SecurityService
    from TimeLocker.security.credential_manager import CredentialManager
    from TimeLocker.interfaces.recovery_models import (
        RecoveryOperation,
        RecoveryType,
        OperationStatus,
        ProgressStatus
    )
    
    # Create repository
    repo_path = Path("/tmp/demo_security_repo")
    repo_path.mkdir(parents=True, exist_ok=True)
    
    repository = BackupRepository(
        location=str(repo_path),
        password="demo_password_123"
    )
    
    # Initialize repository if needed
    if not repository.is_repository_initialized():
        repository.initialize_repository()
    
    # Create security service
    credential_manager = CredentialManager()
    security_service = SecurityService(
        credential_manager=credential_manager,
        config_dir=Path("/tmp/demo_security_config")
    )
    
    # Create recovery orchestrator with security service
    orchestrator = RecoveryOrchestrator(
        repository=repository,
        security_service=security_service
    )
    
    print("Security Integration Features:")
    print("-" * 40)
    print("1. Operation Auditing")
    print("   - Logs recovery operation start/completion")
    print("   - Records operation metadata")
    print("   - Tracks success/failure status\n")
    
    print("2. Encryption Key Management")
    print("   - Validates encryption keys for snapshots")
    print("   - Verifies repository encryption status")
    print("   - Ensures decryption capability\n")
    
    print("3. Access Control Validation")
    print("   - Checks target path permissions")
    print("   - Validates write access")
    print("   - Ensures secure recovery locations\n")
    
    # Create a test operation
    operation = RecoveryOperation(
        operation_id="test_op_123",
        snapshot_id="test_snapshot",
        recovery_type=RecoveryType.FULL,
        target_path="/tmp/demo_recovery_target",
        status=OperationStatus.RUNNING,
        start_time=datetime.now()
    )
    operation.progress = ProgressStatus()
    
    # Demonstrate auditing
    print("Auditing recovery operation...")
    orchestrator._audit_recovery_operation(
        operation,
        'running',
        {'phase': 'demonstration'}
    )
    print("✓ Operation audited successfully\n")
    
    # Validate encryption keys
    try:
        print("Validating encryption keys...")
        orchestrator._validate_encryption_keys("test_snapshot")
        print("✓ Encryption keys validated\n")
    except Exception as e:
        print(f"✗ Encryption validation failed: {e}\n")
    
    # Validate access control
    target_path = Path("/tmp/demo_recovery_target")
    target_path.mkdir(parents=True, exist_ok=True)
    
    try:
        print(f"Validating access control for: {target_path}")
        orchestrator._validate_target_access_control(str(target_path))
        print("✓ Access control validated\n")
    except Exception as e:
        print(f"✗ Access control validation failed: {e}\n")
    
    # Show audit log summary
    print("Security audit summary:")
    summary = security_service.get_security_summary(days=1)
    print(f"  Total events: {summary['total_events']}")
    print(f"  Events by type: {summary['events_by_type']}")
    print(f"  Events by level: {summary['events_by_level']}\n")
    
    print("Security integration ensures safe and auditable recovery operations!")


def demo_integrated_recovery():
    """
    Demonstrate a complete recovery operation with all service integrations.
    
    This shows how all services work together during a recovery operation.
    """
    print("\n" + "=" * 80)
    print("DEMO: Integrated Recovery Operation")
    print("=" * 80 + "\n")
    
    from TimeLocker.backup_repository import BackupRepository
    from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
    from TimeLocker.services.repository_service import RepositoryService
    from TimeLocker.services.validation_service import ValidationService
    from TimeLocker.utils.performance_utils import PerformanceModule
    from TimeLocker.security.security_service import SecurityService
    from TimeLocker.security.credential_manager import CredentialManager
    from TimeLocker.selection_manager import SelectionManager
    from TimeLocker.interfaces.recovery_models import RecoveryOptions
    
    # Create repository
    repo_path = Path("/tmp/demo_integrated_repo")
    repo_path.mkdir(parents=True, exist_ok=True)
    
    repository = BackupRepository(
        location=str(repo_path),
        password="demo_password_123"
    )
    
    # Initialize repository if needed
    if not repository.is_repository_initialized():
        print("Initializing repository...")
        repository.initialize_repository()
        print("✓ Repository initialized\n")
    
    # Create all services
    validation_service = ValidationService()
    performance_module = PerformanceModule()
    repository_service = RepositoryService(
        validation_service=validation_service,
        performance_module=performance_module
    )
    
    credential_manager = CredentialManager()
    security_service = SecurityService(
        credential_manager=credential_manager,
        config_dir=Path("/tmp/demo_integrated_security")
    )
    
    selection_manager = SelectionManager()
    
    # Create fully integrated recovery orchestrator
    orchestrator = RecoveryOrchestrator(
        repository=repository,
        repository_service=repository_service,
        security_service=security_service,
        selection_manager=selection_manager
    )
    
    print("Integrated Recovery Workflow:")
    print("-" * 40)
    print("1. Repository validation (Repository Service)")
    print("2. Conflict detection (Repository Service + Security Service)")
    print("3. Authentication validation (Security Service)")
    print("4. Selection template application (Selection Manager)")
    print("5. Selection criteria validation (Selection Manager)")
    print("6. Encryption key validation (Security Service)")
    print("7. Access control validation (Security Service)")
    print("8. Recovery execution")
    print("9. Operation auditing (Security Service)")
    print("10. Progress monitoring\n")
    
    print("All services work together to ensure:")
    print("  ✓ Safe repository access")
    print("  ✓ Validated file selection")
    print("  ✓ Secure recovery operations")
    print("  ✓ Complete audit trail")
    print("  ✓ Proper error handling\n")
    
    print("The integrated approach provides comprehensive recovery capabilities!")


def main():
    """Run all integration demos."""
    print("\n" + "=" * 80)
    print("RECOVERY OPERATIONS SERVICE INTEGRATION DEMONSTRATION")
    print("=" * 80)
    
    # Demo 1: Repository Integration
    demo_repository_integration()
    
    # Demo 2: Selection Integration (async)
    asyncio.run(demo_selection_integration())
    
    # Demo 3: Security Integration
    demo_security_integration()
    
    # Demo 4: Integrated Recovery
    demo_integrated_recovery()
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("1. Repository Management ensures safe repository access")
    print("2. Data Selection enables flexible file recovery")
    print("3. Security Services provide auditing and access control")
    print("4. All services integrate seamlessly for comprehensive recovery")
    print("\nFor more information, see:")
    print("  - docs/guides/user/recovery-operations-guide.md")
    print("  - docs/reference/recovery-operations-api.md")
    print()


if __name__ == "__main__":
    main()
