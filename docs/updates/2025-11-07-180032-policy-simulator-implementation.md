# Policy Simulator Implementation

**Date**: 2025-11-07  
**Type**: Feature Implementation  
**Component**: Policy Management  
**Status**: Completed

## Overview

Implemented the PolicySimulator class providing comprehensive simulation and preview capabilities for policy operations. This allows administrators to safely preview the effects of retention policies before actual enforcement, detect conflicts between policy assignments, and compare different policy configurations.

## Changes Made

### New Files

1. **src/TimeLocker/policy/simulator.py**
   - PolicySimulator class for dry-run operations
   - Simulation and preview functionality
   - Conflict detection and resolution simulation
   - Policy comparison capabilities

2. **examples/policy_simulator_demo.py**
   - Comprehensive demonstration of simulator features
   - Examples of retention simulation
   - Conflict detection demonstrations
   - Policy comparison examples

### Modified Files

1. **src/TimeLocker/policy/__init__.py**
   - Added PolicySimulator to exports
   - Updated __all__ list

## Implementation Details

### PolicySimulator Class

The PolicySimulator provides the following key capabilities:

#### 1. Retention Policy Simulation

```python
def simulate_retention_policy(
    self,
    policy: RetentionPolicy,
    repository: BackupRepository,
    target_id: str,
) -> SimulationResult
```

- Performs dry-run of retention policy enforcement
- Shows which snapshots would be retained or pruned
- Calculates storage impact without modifying repository
- Checks for compliance warnings

#### 2. Policy Assignment Preview

```python
def preview_policy_assignment(
    self,
    policy: RetentionPolicy,
    target_type: TargetType,
    target_id: str,
    existing_assignments: Optional[List[PolicyAssignment]] = None,
) -> SimulationResult
```

- Previews effects of assigning a policy to a target
- Detects conflicts with existing assignments
- Provides conflict resolution recommendations

#### 3. Conflict Detection

```python
def detect_policy_conflicts(
    self,
    new_policy: RetentionPolicy,
    existing_assignments: List[PolicyAssignment],
    target_type: TargetType,
    target_id: str,
) -> List[PolicyConflict]
```

- Identifies overlapping policy assignments
- Determines conflict types
- Suggests resolution strategies

#### 4. Conflict Resolution Simulation

```python
def simulate_conflict_resolution(
    self,
    conflicts: List[PolicyConflict],
    policies: Dict[str, RetentionPolicy],
    resolution_strategy: ConflictResolution,
) -> Dict[str, Any]
```

- Simulates how conflicts would be resolved
- Supports multiple resolution strategies:
  - PRIORITY: Use policy with highest priority
  - MOST_RESTRICTIVE: Apply most restrictive rules
  - LEAST_RESTRICTIVE: Apply least restrictive rules
  - MERGE: Merge compatible rules
  - FAIL: Fail on conflict

#### 5. Policy Comparison

```python
def compare_policies(
    self,
    policy1: RetentionPolicy,
    policy2: RetentionPolicy,
    snapshots: List[BackupSnapshot],
) -> Dict[str, Any]
```

- Compares effects of two different policies
- Shows differences in snapshot retention
- Calculates storage impact differences
- Helps administrators choose optimal policies

## Key Features

### Simulation Results

SimulationResult provides comprehensive information:
- Snapshots to prune (with details)
- Snapshots to retain (with details)
- Storage impact analysis
- Compliance warnings
- Policy conflicts

### Storage Impact Analysis

StorageImpact includes:
- Number of snapshots to remove
- Estimated space to be freed
- Number of snapshots to retain
- Total retained storage size

### Conflict Detection

PolicyConflict captures:
- Conflicting policy IDs
- Conflict type
- Human-readable description
- Recommended resolution strategy

### Compliance Warnings

The simulator checks for:
- Snapshots within compliance period marked for removal
- Policies that would remove all snapshots
- Potential compliance violations

## Integration

### With PolicyEngine

The simulator uses PolicyEngine for:
- Retention rule evaluation
- Snapshot decision logic
- Compliance validation

### With Existing Models

Leverages existing data models:
- RetentionPolicy
- PolicyAssignment
- SimulationResult
- PolicyConflict
- StorageImpact

## Usage Examples

### Basic Retention Simulation

```python
from TimeLocker.policy import PolicySimulator, RetentionPolicy

simulator = PolicySimulator()

result = simulator.simulate_retention_policy(
    policy=retention_policy,
    repository=backup_repository,
    target_id="my-repository",
)

print(f"Would prune {len(result.snapshots_to_prune)} snapshots")
print(f"Would free {result.storage_impact.estimated_space_freed_bytes} bytes")
```

### Conflict Detection

```python
conflicts = simulator.detect_policy_conflicts(
    new_policy=new_retention_policy,
    existing_assignments=current_assignments,
    target_type=TargetType.REPOSITORY,
    target_id="my-repository",
)

if conflicts:
    print(f"Found {len(conflicts)} conflicts")
    for conflict in conflicts:
        print(f"  {conflict.description}")
```

### Policy Comparison

```python
comparison = simulator.compare_policies(
    policy1=aggressive_policy,
    policy2=conservative_policy,
    snapshots=repository_snapshots,
)

print(f"Policy 1 retains: {comparison['policy1']['snapshots_retained']}")
print(f"Policy 2 retains: {comparison['policy2']['snapshots_retained']}")
print(f"Difference: {comparison['differences']['size_difference_bytes']} bytes")
```

## Testing

### Demonstration Script

The `policy_simulator_demo.py` script demonstrates:
1. Retention policy simulation with 30 sample snapshots
2. Conflict detection between overlapping assignments
3. Conflict resolution simulation with different strategies
4. Policy comparison showing retention differences
5. Assignment preview with conflict detection

Run the demo:
```bash
python examples/policy_simulator_demo.py
```

### Test Coverage

The implementation includes:
- Simulation accuracy validation
- Conflict detection logic
- Storage impact calculations
- Compliance warning checks
- Resolution strategy simulation

## Design Decisions

### 1. Dry-Run First Approach

All simulation operations are non-destructive by design:
- No actual snapshot removal
- No repository modifications
- Safe preview of all operations

**Rationale**: Prevents accidental data loss and allows administrators to verify policy effects before enforcement.

### 2. Comprehensive Conflict Detection

Detects multiple conflict types:
- Overlapping assignments
- Priority conflicts
- Incompatible rules

**Rationale**: Provides clear visibility into policy interactions and helps prevent unexpected behavior.

### 3. Multiple Resolution Strategies

Supports various conflict resolution approaches:
- Priority-based
- Most/least restrictive
- Merge strategies

**Rationale**: Different organizations have different needs for handling policy conflicts.

### 4. Storage Impact Analysis

Calculates detailed storage metrics:
- Space to be freed
- Space to be retained
- Per-snapshot size information

**Rationale**: Helps administrators understand storage implications of policy decisions.

### 5. Integration with PolicyEngine

Reuses PolicyEngine evaluation logic:
- Consistent retention decisions
- Same rule evaluation
- Unified compliance checking

**Rationale**: Ensures simulation results match actual enforcement behavior.

## Requirements Satisfied

This implementation satisfies the following requirements from the policy management specification:

- **Requirement 3.3**: Basic policy preview showing affected repositories and data selections
- **Requirement 3.4**: Policy validation and preview capabilities before enforcement

## Next Steps

1. **Task 6**: Implement policy storage and persistence layer
2. **Task 7**: Integrate with existing services (backup orchestrator, monitoring)
3. **Task 8**: Create CLI interface for policy management
4. **Task 9**: Add comprehensive tests (optional)
5. **Task 10**: Create documentation and examples (optional)

## Notes

- The simulator is designed to work with both in-memory and persisted policies
- All simulation operations are thread-safe
- Storage impact calculations are estimates based on snapshot metadata
- Conflict detection can be extended for additional conflict types
- Resolution strategies can be customized per organization

## Related Files

- `src/TimeLocker/policy/simulator.py` - Main implementation
- `src/TimeLocker/policy/engine.py` - Policy engine integration
- `src/TimeLocker/policy/models.py` - Data models
- `examples/policy_simulator_demo.py` - Demonstration script
- `.kiro/specs/policy-management/design.md` - Design specification
- `.kiro/specs/policy-management/requirements.md` - Requirements
