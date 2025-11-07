# CLI Refactoring Plan

## Executive Summary

The TimeLocker CLI (`cli.py`) has grown to 5,780 lines, making it difficult to maintain, test, and extend. This document outlines a three-phase refactoring plan to modularize the codebase while maintaining backward compatibility.

## Current State

- **File Size**: 5,780 lines
- **Command Functions**: 67
- **Helper Functions**: 91
- **Command Groups**: 8 (backup, snapshots, repos, targets, config, credentials, security, main)

## Goals

1. **Maintainability**: Reduce file sizes to 200-400 lines per module
2. **Testability**: Enable isolated testing of components
3. **Collaboration**: Allow multiple developers to work simultaneously
4. **Performance**: Improve import times through lazy loading
5. **Extensibility**: Make it easier to add new commands

## Three-Phase Approach

### Phase 1: Extract Helpers ✅ COMPLETED

**Goal**: Extract reusable utility functions into dedicated modules

**Structure**:
```
src/TimeLocker/cli/
├── helpers/
│   ├── display.py              # Panel display functions
│   ├── logging_setup.py        # Logging configuration
│   ├── service_helpers.py      # Service layer integration
│   ├── auth_helpers.py         # Authentication helpers
│   └── repository_helpers.py   # Repository utilities
└── test_compatibility.py       # Test patches
```

**Benefits**:
- Immediate code reusability
- Clear separation of concerns
- Foundation for Phase 2

**Status**: ✅ Complete - Helpers extracted and documented

---

### Phase 2: Split Command Groups 🔄 NEXT

**Goal**: Separate command groups into individual modules

**Structure**:
```
src/TimeLocker/cli/commands/
├── backup.py              # ~200 lines
├── snapshots.py           # ~800 lines
├── repositories.py        # ~1200 lines
├── targets.py             # ~400 lines
├── config.py              # ~1500 lines
├── credentials.py         # ~400 lines
└── security.py            # ~300 lines
```

**Implementation Steps**:

1. **Create Package Structure**
   ```bash
   mkdir -p src/TimeLocker/cli/commands
   touch src/TimeLocker/cli/commands/__init__.py
   ```

2. **Extract One Command Group** (Proof of Concept)
   - Start with `targets.py` (smallest, ~400 lines)
   - Move command functions and decorators
   - Update imports
   - Run tests

3. **Migrate Remaining Groups**
   - One group at a time
   - Full test suite after each migration
   - Document any issues

4. **Update Main CLI**
   - Import command groups
   - Register with Typer apps
   - Maintain backward compatibility

**Example: targets.py**
```python
"""Backup target management commands."""

from typing import Optional, Annotated
from pathlib import Path
import typer
from ..helpers import (
    show_success_panel,
    show_error_panel,
    setup_logging,
    _get_service_manager_for_command,
)

targets_app = typer.Typer(help="Backup target operations")

@targets_app.command("list")
def targets_list(
    verbose: Annotated[bool, typer.Option(...)] = False,
    json_output: Annotated[bool, typer.Option(...)] = False,
) -> None:
    """List configured backup targets."""
    setup_logging(verbose)
    # ... implementation
```

**Benefits**:
- Manageable file sizes
- Easier navigation
- Parallel development
- Faster imports

**Estimated Effort**: 2-3 days

---

### Phase 3: Consolidate Patterns 📋 PLANNED

**Goal**: Reduce code duplication through base classes and shared patterns

**Components**:

1. **Base Command Class**
   ```python
   class BaseCommand:
       """Base class for CLI commands with common setup."""
       
       @staticmethod
       def setup(verbose: bool, config_dir: Optional[Path]):
           """Common setup for all commands."""
           setup_logging(verbose, config_dir)
           return _create_configuration_module(config_dir)
       
       @staticmethod
       def handle_error(e: Exception, verbose: bool, title: str):
           """Common error handling."""
           show_error_panel(title, str(e))
           if verbose:
               console.print_exception()
           raise typer.Exit(1)
   ```

2. **Command Decorators**
   - `@with_config` - Auto-inject configuration
   - `@with_logging` - Auto-setup logging
   - `@with_error_handling` - Wrap in try/except

3. **Shared Validators**
   - Repository name validation
   - Path validation
   - Snapshot ID validation

**Benefits**:
- Reduced code duplication
- Consistent error handling
- Easier to add new commands
- Better testing coverage

**Estimated Effort**: 3-4 days

---

## Migration Strategy

### Backward Compatibility

**Critical Requirements**:
- No breaking changes to CLI interface
- All existing tests must pass
- Import paths remain valid
- Command behavior unchanged

**Compatibility Layer**:
```python
# cli/__init__.py maintains backward compatibility
from .app import app
from .helpers import *  # Re-export helpers

# Legacy import support
__all__ = ["app", "show_success_panel", "show_error_panel", ...]
```

### Testing Strategy

**Test Levels**:

1. **Unit Tests** - Individual helper/command modules
2. **Integration Tests** - Command groups with services
3. **Regression Tests** - Existing CLI test suite
4. **End-to-End Tests** - Complete workflows

**Test Commands**:
```bash
# Run all tests
pytest tests/ -v

# Run CLI-specific tests
pytest tests/test_cli.py -v

# Run with coverage
pytest tests/ --cov=src/TimeLocker/cli --cov-report=html
```

### Rollback Plan

If issues arise:

1. **Phase 1**: Revert helper extraction, restore original imports
2. **Phase 2**: Keep helpers, revert command separation
3. **Phase 3**: Keep Phases 1-2, revert base classes

Each phase is independently reversible.

---

## Success Metrics

### Code Quality

- ✅ No file exceeds 500 lines
- ✅ All functions have type hints
- ✅ All modules have docstrings
- ✅ Test coverage > 80%

### Performance

- ✅ CLI startup time < 200ms
- ✅ Import time reduced by 30%
- ✅ No memory regression

### Maintainability

- ✅ New commands can be added in < 1 hour
- ✅ Code review time reduced by 50%
- ✅ Onboarding time for new developers reduced

---

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Extract Helpers | 1 day | ✅ Complete |
| Phase 2: Split Commands | 2-3 days | 🔄 Next |
| Phase 3: Consolidate Patterns | 3-4 days | 📋 Planned |
| **Total** | **6-8 days** | **In Progress** |

---

## Risk Assessment

### High Risk
- **Import errors**: Mitigated by backward compatibility layer
- **Test failures**: Mitigated by incremental approach with full test suite

### Medium Risk
- **Performance regression**: Mitigated by benchmarking
- **Documentation drift**: Mitigated by updating docs with each phase

### Low Risk
- **User impact**: No CLI interface changes
- **Deployment issues**: No deployment changes required

---

## Resources

### Documentation
- [Phase 1 Implementation](../updates/2025-11-07-cli-refactoring-phase1.md)
- [Coding Standards](../../.kiro/steering/coding-standards.md)
- [General Preferences](../../.kiro/steering/general-preferences.md)

### Related Work
- Plugin architecture implementation
- Repository management refactoring
- Configuration backup system

---

## Approval Checklist

### Phase 1 ✅
- [x] Helper modules created
- [x] Test compatibility maintained
- [x] Documentation complete
- [ ] All tests passing
- [ ] Code review approved

### Phase 2 (Pending)
- [ ] Command modules created
- [ ] Imports updated
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Code review approved

### Phase 3 (Pending)
- [ ] Base classes implemented
- [ ] Commands refactored
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Code review approved

---

## Next Actions

1. ✅ Complete Phase 1 helper extraction
2. ⏳ Update `cli.py` to use new helpers
3. ⏳ Run full test suite
4. ⏳ Begin Phase 2: Extract targets.py as proof of concept
5. ⏳ Document Phase 2 progress

---

## Questions & Decisions

### Q: Should we maintain the original cli.py?
**A**: Yes, during transition. Remove after Phase 3 complete and all tests pass.

### Q: How to handle circular imports?
**A**: Use TYPE_CHECKING and forward references. Keep dependencies unidirectional.

### Q: What about CLI entry point?
**A**: Entry point remains `TimeLocker.cli:app`. Internal structure transparent to users.

### Q: How to version this change?
**A**: Internal refactoring, no version bump. Document in changelog as "Internal: CLI refactoring for maintainability"

---

## Conclusion

This three-phase refactoring plan provides a structured approach to improving CLI maintainability while minimizing risk. Phase 1 is complete, establishing the foundation for command separation in Phase 2 and pattern consolidation in Phase 3.

The incremental approach ensures backward compatibility and allows for rollback at any stage if issues arise.
