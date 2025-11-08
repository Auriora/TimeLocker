# Policy Management Module

**Last Updated**: 2025-11-08  
**Status**: Active Development  
**Location**: `src/TimeLocker/policy/`

This module provides centralized configuration and enforcement of backup and retention policies within the TimeLocker platform.

## Module Structure

```
policy/
├── __init__.py           # Module exports and public API
├── types.py             # Enums and type definitions
├── exceptions.py        # Policy-specific exceptions
├── models.py            # Core data models
├── validator.py         # Policy validation and compatibility checking
├── engine.py            # Policy execution (future)
├── manager.py           # Policy orchestration (future)
├── simulator.py         # Policy simulation (future)
└── storage.py           # Policy persistence (future)
```

## Components

### Types (`types.py`)

Defines enumeration types for type safety:

- **PolicyType**: Types of policies (BACKUP, RETENTION, COMBINED)
- **TargetType**: Types of targets for policy assignment (REPOSITORY, BACKUP_JOB, BACKUP_TARGET, SYSTEM)
- **EnforcementType**: Types of enforcement operations (SCHEDULED, MANUAL, BACKUP_TRIGGERED, MAINTENANCE, SIMULATION)
- **RetentionType**: Types of retention rules (LAST, HOURLY, DAILY, WEEKLY, MONTHLY, YEARLY, TAG_BASED)
- **PolicyStatus**: Status of a policy (ACTIVE, INACTIVE, DRAFT, ARCHIVED, ERROR)
- **ConflictResolution**: Strategies for resolving policy conflicts

### Exceptions (`exceptions.py`)

Comprehensive exception hierarchy for policy operations:

- **PolicyError**: Base exception for all policy-related errors
- **PolicyValidationError**: Invalid policy configuration
- **PolicyCompatibilityError**: Policy incompatible with target system
- **PolicyEnforcementError**: Policy enforcement failure
- **ComplianceViolationError**: Operation would violate compliance requirements
- **PolicyNotFoundError**: Requested policy does not exist
- **PolicyAssignmentError**: Policy assignment operation failure

### Models (`models.py`)

Core data models using dataclasses:

#### Policy Models
- **BackupPolicy**: Comprehensive backup operation configuration
- **RetentionPolicy**: Snapshot lifecycle and retention rules
- **RetentionRule**: Individual retention rule specification
- **PolicyAssignment**: Associates policies with specific targets

#### Supporting Models
- **ScheduleConfig**: Configuration for scheduled policy operations
- **ComplianceRule**: Compliance requirement definition
- **TagBasedRule**: Tag-based retention rule
- **SnapshotInfo**: Information about a snapshot for policy operations
- **StorageImpact**: Storage impact analysis for policy operations
- **PolicyConflict**: Represents a conflict between policies

#### Enforcement and Audit Models
- **EnforcementRecord**: Records policy enforcement execution
- **SimulationResult**: Results from policy simulation
- **ComplianceStatus**: Policy compliance assessment
- **ComplianceViolation**: Represents a compliance rule violation
- **RequiredAction**: Represents a required action for policy compliance

### Validator (`validator.py`)

Validates policy configurations and compatibility:

- **PolicyValidator**: Main validator class for all policy validation operations
- **ValidationResult**: Result of policy validation with issues and warnings
- **ValidationIssue**: Individual validation issue with severity and details
- **CompatibilityResult**: Result of compatibility checking between policies and targets

The PolicyValidator provides:
- Backup policy validation (configuration, dependencies, completeness)
- Retention policy validation (rules, constraints, conflicts)
- Repository compatibility checking (backup tool support, repository type)
- Policy assignment validation (target compatibility, reference checking)
- Retention compatibility checking (backup tool feature support)

## Usage Examples

### Creating a Retention Policy

```python
from TimeLocker.policy import RetentionPolicy, RetentionRule, RetentionType, PolicyStatus

retention_policy = RetentionPolicy(
    id='rp-standard',
    name='Standard Retention',
    description='Keep 7 daily, 4 weekly, 12 monthly snapshots',
    rules=[
        RetentionRule(type=RetentionType.DAILY, count=7),
        RetentionRule(type=RetentionType.WEEKLY, count=4),
        RetentionRule(type=RetentionType.MONTHLY, count=12),
    ],
    status=PolicyStatus.ACTIVE
)
```

### Creating a Backup Policy

```python
from TimeLocker.policy import BackupPolicy, PolicyStatus

backup_policy = BackupPolicy(
    id='bp-home',
    name='Daily Home Backup',
    description='Daily backup of home directory',
    data_selection_refs=['home-selection'],
    target_repositories=['local-repo'],
    backup_tool='restic',
    retention_policy_id='rp-standard',
    status=PolicyStatus.ACTIVE
)
```

### Assigning a Policy

```python
from TimeLocker.policy import PolicyAssignment, PolicyType, TargetType

assignment = PolicyAssignment(
    id='pa-001',
    policy_id='bp-home',
    policy_type=PolicyType.BACKUP,
    target_type=TargetType.REPOSITORY,
    target_id='local-repo',
    priority=10,
    active=True
)
```

### Validating Policies

```python
from TimeLocker.policy import PolicyValidator, BackupPolicy, RetentionPolicy

validator = PolicyValidator()

# Validate a backup policy
backup_policy = BackupPolicy(
    id='bp-001',
    name='Daily Backup',
    description='Daily backup policy',
    data_selection_refs=['home-selection'],
    target_repositories=['local-repo'],
    backup_tool='restic',
    status=PolicyStatus.ACTIVE
)

try:
    result = validator.validate_backup_policy(backup_policy)
    if result.valid:
        print("✓ Policy is valid")
    else:
        for issue in result.issues:
            print(f"  {issue.severity}: {issue.message}")
except PolicyValidationError as e:
    print(f"Validation failed: {e}")

# Check repository compatibility
repo_config = {
    'name': 's3-repo',
    'uri': 's3:s3.amazonaws.com/bucket',
    'enabled': True,
    'read_only': False,
}

try:
    compat_result = validator.check_repository_compatibility(backup_policy, repo_config)
    if compat_result.compatible:
        print("✓ Policy is compatible with repository")
except PolicyCompatibilityError as e:
    print(f"Incompatible: {e}")
```

### Handling Exceptions

```python
from TimeLocker.policy import PolicyValidationError

try:
    # Policy operation that might fail
    validate_policy(policy)
except PolicyValidationError as e:
    print(f"Validation failed for policy {e.policy_id}")
    for error in e.validation_errors:
        print(f"  - {error}")
```

## Design Principles

1. **Type Safety**: All models use dataclasses with type hints for compile-time checking
2. **Immutability**: Models are designed to be immutable where appropriate
3. **Serialization**: All models provide `to_dict()` methods for JSON serialization
4. **Validation**: Models validate their configuration in `__post_init__` methods
5. **Consistency**: Follows TimeLocker's existing patterns for configuration and error handling
6. **SOLID Principles**: Each component has a single, well-defined responsibility

## Integration Points

This module integrates with:

- **Configuration Management**: Policy storage and retrieval
- **Backup Orchestration**: Policy-driven backup operations
- **Repository Management**: Policy enforcement on repositories
- **Monitoring & Reporting**: Policy compliance tracking
- **CLI**: Policy management commands

## Future Components

The following components will be added in subsequent tasks:

- **PolicyEngine**: Executes policy enforcement operations
- **PolicyManager**: Central orchestrator for policy operations
- **PolicySimulator**: Provides dry-run capabilities for policy preview
- **Policy Storage**: Persistence layer for policies and audit trails

## Requirements Traceability

This module implements:

- **Requirement 1.1**: Policy creation and configuration (models.py)
- **Requirement 1.2**: Retention policy configuration with time-based rules (models.py)
- **Requirement 1.3**: Policy validation during configuration (validator.py)
- **Requirement 2.1**: Policy assignment to repositories and backup operations (models.py)
- **Requirement 3.1**: Policy configuration validation for completeness (validator.py)
- **Requirement 3.2**: Repository existence and accessibility checking (validator.py)
- **Requirement 3.4**: Policy validation for compatibility with repositories and backup tools (validator.py)
- **Requirement 3.5**: Specific error messages for validation failures (validator.py, exceptions.py)
- **Requirement 4.1**: Audit logging of policy operations (models.py)

## Testing

To verify the module is working correctly:

```bash
python3 -c "from TimeLocker.policy import *; print('✅ Policy module loaded successfully')"
```

For comprehensive testing, see `tests/TimeLocker/policy/` (to be created in future tasks).

## Related Documentation

- [Requirements](../1-requirements/)
- [Architecture Overview](../2-architecture/overview.md)
- [Testing Documentation](../4-testing/)
