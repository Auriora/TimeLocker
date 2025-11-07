# Phase 2 Completion Plan

**Status**: Roadmap for completing command extraction  
**Remaining**: 60 commands across 5 modules

## Current Status

✅ **Completed** (7 commands, 2 modules):
- targets.py (5 commands, 330 lines)
- backup.py (2 commands, 420 lines)

🔄 **Remaining** (60 commands, 5 modules):
- security.py (7 commands, ~300 lines)
- credentials.py (8 commands, ~400 lines)
- snapshots.py (10 commands, ~800 lines)
- repositories.py (15 commands, ~1,200 lines)
- config.py (20 commands, ~1,500 lines)

## Extraction Strategy

### Option 1: Manual Extraction (Thorough)
Extract each module one at a time with full testing.

**Pros**: Thorough, tested, safe  
**Cons**: Time-consuming (2-3 days)

### Option 2: Batch Extraction (Fast)
Extract all modules at once using templates.

**Pros**: Fast (4-6 hours)  
**Cons**: Requires comprehensive testing afterward

### Option 3: Hybrid Approach (Recommended)
Extract using templates with Phase 3 patterns, test incrementally.

**Pros**: Fast + quality  
**Cons**: Moderate effort (1-2 days)

## Recommended: Hybrid Approach

### Step 1: Create Module Templates

Use Phase 3 base classes for all new modules:

```python
# Template for new command module
from .base import (
    create_typer_app,
    with_error_handling,
    with_logging,
    VerboseOption,
    JsonOption,
    YesOption,
    show_success_panel,
    show_error_panel,
    console,
    _get_service_method,
    _call_service_method,
)

# Create app
{module}_app = create_typer_app("{module}", "{description}")

# Commands follow Phase 3 patterns
@{module}_app.command("list")
@with_error_handling("List Error")
@with_logging
def {module}_list(verbose: VerboseOption = False):
    """List items."""
    # Implementation
    pass
```

### Step 2: Extract by Priority

1. **security.py** (7 commands) - Smallest remaining
2. **credentials.py** (8 commands) - Related to security
3. **snapshots.py** (10 commands) - Medium complexity
4. **repositories.py** (15 commands) - High complexity
5. **config.py** (20 commands) - Largest, most complex

### Step 3: Test Incrementally

After each module:
1. Check imports work
2. Run diagnostics
3. Test one command manually
4. Update commands/__init__.py

### Step 4: Final Integration

1. Update main cli.py to import from cli_modules
2. Run full test suite
3. Verify no regressions
4. Update documentation

## Module Extraction Details

### Security Module (7 commands)

**Commands**:
- `security status` - Show security status
- `security logs` - View security logs
- `security notifications` - View notifications
- `security sessions` - View active sessions
- `security cleanup` - Clean up old data
- `security config` - Security configuration
- `security audit` - Security audit (if exists)

**Estimated Lines**: ~300  
**Complexity**: Low-Medium  
**Dependencies**: SecurityService, AccessManager

**Template**:
```python
# cli_modules/commands/security.py
from .base import create_typer_app, with_error_handling, with_logging
from TimeLocker.security import SecurityService, AccessManager

security_app = create_typer_app("security", "Security management commands")

@security_app.command("status")
@with_error_handling("Security Status Error")
@with_logging
def security_status(...):
    # Implementation from cli.py lines 5319-5410
    pass
```

### Credentials Module (8 commands)

**Commands**:
- `credentials unlock` - Unlock credential manager
- `credentials store` - Store credentials
- `credentials set` - Set credential
- `credentials list` - List credentials
- `credentials remove` - Remove credential
- `credentials show` - Show credential
- `credentials lock` - Lock credential manager
- `credentials change-password` - Change master password

**Estimated Lines**: ~400  
**Complexity**: Medium  
**Dependencies**: CredentialManager

### Snapshots Module (10 commands)

**Commands**:
- `snapshots list` - List snapshots
- `snapshots show` - Show snapshot details
- `snapshots restore` - Restore from snapshot
- `snapshots contents` - List snapshot contents
- `snapshots mount` - Mount snapshot
- `snapshots umount` - Unmount snapshot
- `snapshots forget` - Delete snapshot
- `snapshots find` - Find files in snapshots
- `snapshots find-in` - Find in specific snapshot
- `snapshots prune` - Prune old snapshots
- `snapshots diff` - Compare snapshots

**Estimated Lines**: ~800  
**Complexity**: High  
**Dependencies**: SnapshotManager, RestoreManager

### Repositories Module (15 commands)

**Commands**:
- `repos list` - List repositories
- `repos add` - Add repository
- `repos show` - Show repository details
- `repos remove` - Remove repository
- `repos update` - Update repository
- `repos default` - Set default repository
- `repos clear-default` - Clear default
- `repos lock` - Lock repository
- `repos unlock` - Unlock repository
- `repos mode` - Set repository mode
- `repos protection-status` - Show protection status
- `repos init` - Initialize repository
- `repos migrate` - Migrate repository
- `repos forget` - Forget data
- `repos check` - Check repository
- `repos stats` - Repository statistics
- `repos check-all` - Check all repositories
- `repos stats-all` - Stats for all repositories
- `repos credentials set` - Set repository credentials
- `repos credentials remove` - Remove credentials
- `repos credentials show` - Show credentials

**Estimated Lines**: ~1,200  
**Complexity**: Very High  
**Dependencies**: RepositoryManager, RepositoryService

### Config Module (20 commands)

**Commands**:
- `config show` - Show configuration
- `config setup` - Configuration wizard
- `config validate` - Validate configuration
- `config diff` - Compare configurations
- `config health-check` - Health check
- `config backup-list` - List config backups
- `config backup-create` - Create backup
- `config backup-restore` - Restore backup
- `config backup-compare` - Compare backups
- `config lock-status` - Lock status
- `config lock-cleanup` - Clean up locks
- `config performance` - Performance metrics
- `config import restic` - Import from restic
- `config import timeshift` - Import from timeshift
- Plus sub-commands for various config operations

**Estimated Lines**: ~1,500  
**Complexity**: Very High  
**Dependencies**: ConfigurationManager, ConfigurationModule

## Implementation Timeline

### Day 1: Small Modules
- Morning: Extract security.py (7 commands)
- Afternoon: Extract credentials.py (8 commands)
- Evening: Test both modules

### Day 2: Medium Modules
- Morning: Extract snapshots.py (10 commands)
- Afternoon: Test snapshots module
- Evening: Start repositories.py

### Day 3: Large Modules
- Morning: Complete repositories.py (15 commands)
- Afternoon: Extract config.py (20 commands)
- Evening: Integration testing

### Day 4: Testing & Documentation
- Morning: Full test suite
- Afternoon: Fix any issues
- Evening: Update documentation

## Quick Start Guide

### For Each Module:

1. **Create file**: `src/TimeLocker/cli_modules/commands/{module}.py`

2. **Add header**:
```python
"""
{Module} management commands.

This module contains CLI commands for {description}.
"""

from .base import (
    create_typer_app,
    with_error_handling,
    with_logging,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    _get_service_method,
    _call_service_method,
)

# Module-specific imports
from TimeLocker import cli as _cli_module
# ... other imports

{module}_app = create_typer_app("{module}", "{description}")
```

3. **Copy commands from cli.py**:
   - Find all `@{module}_app.command()` decorators
   - Copy entire function including decorator
   - Add `@with_error_handling()` and `@with_logging` decorators
   - Replace type annotations with Phase 3 aliases where applicable

4. **Update commands/__init__.py**:
```python
from .{module} import {module}_app
__all__.append("{module}_app")
```

5. **Test**:
```bash
python -c "from TimeLocker.cli_modules.commands import {module}_app; print('✓ OK')"
```

## Automation Script

For faster extraction, consider creating a script:

```python
# scripts/extract_commands.py
import re
from pathlib import Path

def extract_module(module_name: str, start_line: int, end_line: int):
    """Extract commands from cli.py to new module."""
    cli_file = Path("src/TimeLocker/cli.py")
    output_file = Path(f"src/TimeLocker/cli_modules/commands/{module_name}.py")
    
    # Read source
    with open(cli_file) as f:
        lines = f.readlines()
    
    # Extract commands
    commands = lines[start_line:end_line]
    
    # Add header and imports
    header = generate_header(module_name)
    
    # Write output
    with open(output_file, 'w') as f:
        f.write(header)
        f.writelines(commands)
    
    print(f"✓ Created {output_file}")

# Usage
extract_module("security", 5318, 5800)
extract_module("credentials", 3800, 4000)
# etc.
```

## Success Criteria

Phase 2 is complete when:

- [ ] All 67 commands extracted to 7 modules
- [ ] All modules use Phase 3 patterns
- [ ] Zero diagnostic errors
- [ ] All imports work
- [ ] Commands registered in __init__.py
- [ ] Basic smoke tests pass
- [ ] Documentation updated

## Risk Mitigation

### Risk: Breaking existing functionality
**Mitigation**: Keep original cli.py intact, test incrementally

### Risk: Import errors
**Mitigation**: Use consistent import patterns, test after each module

### Risk: Missing dependencies
**Mitigation**: Check all imports before extraction

### Risk: Test failures
**Mitigation**: Run tests after each module, fix immediately

## Next Steps

1. Choose extraction approach (recommend Hybrid)
2. Start with security.py (smallest remaining)
3. Test thoroughly
4. Continue with remaining modules
5. Final integration and testing

## Estimated Effort

- **Manual extraction**: 2-3 days
- **Batch extraction**: 4-6 hours + testing
- **Hybrid approach**: 1-2 days
- **Testing & docs**: 0.5-1 day

**Total**: 1.5-4 days depending on approach

---

**Recommendation**: Use hybrid approach with Phase 3 patterns for best balance of speed and quality.
