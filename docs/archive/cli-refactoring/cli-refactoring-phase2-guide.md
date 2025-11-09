# CLI Refactoring Phase 2: Quick Start Guide

## Overview

Phase 2 extracts command groups from the monolithic `cli.py` into separate modules. This guide provides step-by-step instructions for implementing Phase 2.

## Prerequisites

✅ Phase 1 complete - Helpers extracted  
✅ All tests passing  
✅ No diagnostic errors  

## Goal

Split 67 commands across 7 focused modules:

| Module | Commands | Lines | Priority |
|--------|----------|-------|----------|
| targets.py | 5 | ~400 | 1 (Proof of concept) |
| backup.py | 2 | ~200 | 2 |
| security.py | 7 | ~300 | 3 |
| credentials.py | 8 | ~400 | 4 |
| snapshots.py | 10 | ~800 | 5 |
| repositories.py | 15 | ~1200 | 6 |
| config.py | 20 | ~1500 | 7 |

## Step-by-Step: Extract targets.py (Proof of Concept)

### Step 1: Identify Target Commands

From `cli.py`, find all `@targets_app.command()` decorators:

```bash
grep -n "@targets_app.command" src/TimeLocker/cli.py
```

Expected commands:
- `targets_list`
- `targets_add`
- `targets_show`
- `targets_edit`
- `targets_remove`

### Step 2: Create targets.py Module

```python
# src/TimeLocker/cli/commands/targets.py
"""Backup target management commands."""

from typing import Optional, Annotated, List
from pathlib import Path
import typer
from rich.table import Table

from ..helpers import (
    show_success_panel,
    show_error_panel,
    show_info_panel,
    setup_logging,
    _get_service_manager_for_command,
    _get_service_method,
    console,
)

# Create Typer app for targets
targets_app = typer.Typer(
    help="Backup target operations",
    context_settings={"max_content_width": 110}
)
targets_app.info.options_metavar = "⟨OPTIONS⟩"


@targets_app.command("list")
def targets_list(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format")] = False,
) -> None:
    """List configured backup targets."""
    setup_logging(verbose)
    # ... copy implementation from cli.py


@targets_app.command("add")
def targets_add(
    name: Annotated[str, typer.Argument(help="Target name")],
    path: Annotated[Path, typer.Option("--path", help="Path to backup")],
    # ... other parameters
) -> None:
    """Add a new backup target."""
    setup_logging(verbose)
    # ... copy implementation from cli.py


# ... other target commands
```

### Step 3: Copy Command Implementations

1. Find each command function in `cli.py`
2. Copy the entire function (including decorator and docstring)
3. Paste into `targets.py`
4. Verify all imports are available

### Step 4: Update commands/__init__.py

```python
# src/TimeLocker/cli/commands/__init__.py
"""CLI command modules."""

from .targets import targets_app

__all__ = ["targets_app"]
```

### Step 5: Update cli/__init__.py

```python
# src/TimeLocker/cli/__init__.py
"""TimeLocker Command Line Interface - Refactored modular structure."""

from .commands import targets_app

# Import main app (still in cli.py for now)
from ..cli import app

# Register command groups
app.add_typer(targets_app, name="targets")

__all__ = ["app"]
```

### Step 6: Comment Out Original Commands

In `cli.py`, comment out the extracted commands:

```python
# MOVED TO commands/targets.py
# @targets_app.command("list")
# def targets_list(...):
#     ...
```

### Step 7: Run Tests

```bash
# Run all tests
pytest tests/test_cli.py -v

# Run specific target tests
pytest tests/test_cli.py -k "target" -v

# Check for import errors
python -c "from TimeLocker.cli import app; print('OK')"
```

### Step 8: Verify CLI Works

```bash
# Test help
timelocker targets --help

# Test list command
timelocker targets list

# Test add command (dry run if possible)
timelocker targets add test-target --path /tmp/test
```

## Template for Other Command Groups

Once `targets.py` works, use this template for other groups:

```python
# src/TimeLocker/cli/commands/{group}.py
"""
{Group} management commands.

This module contains all CLI commands for {group} operations.
"""

from typing import Optional, Annotated, List, Dict, Any
from pathlib import Path
from datetime import datetime
import typer
from rich.table import Table
from rich.panel import Panel

from ..helpers import (
    show_success_panel,
    show_error_panel,
    show_info_panel,
    setup_logging,
    format_file_size,
    _get_service_manager_for_command,
    _get_service_method,
    _call_service_method,
    console,
)

# Create Typer app
{group}_app = typer.Typer(
    help="{Group} operations",
    context_settings={"max_content_width": 110}
)
{group}_app.info.options_metavar = "⟨OPTIONS⟩"


@{group}_app.command("list")
def {group}_list(...) -> None:
    """List {group}s."""
    setup_logging(verbose)
    try:
        # Implementation
        show_success_panel("Success", "Operation complete")
    except KeyboardInterrupt:
        show_error_panel("Cancelled", "Operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Error", str(e))
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ... other commands
```

## Extraction Order

### 1. targets.py (Proof of Concept)
- **Why first**: Smallest, simplest commands
- **Commands**: 5
- **Estimated time**: 2 hours
- **Risk**: Low

### 2. backup.py
- **Why second**: Only 2 commands, straightforward
- **Commands**: 2
- **Estimated time**: 1 hour
- **Risk**: Low

### 3. security.py
- **Why third**: Medium complexity, good practice
- **Commands**: 7
- **Estimated time**: 2 hours
- **Risk**: Medium

### 4. credentials.py
- **Why fourth**: Related to security, medium size
- **Commands**: 8
- **Estimated time**: 2 hours
- **Risk**: Medium

### 5. snapshots.py
- **Why fifth**: Larger, more complex
- **Commands**: 10
- **Estimated time**: 3 hours
- **Risk**: Medium

### 6. repositories.py
- **Why sixth**: Large, complex, many dependencies
- **Commands**: 15
- **Estimated time**: 4 hours
- **Risk**: High

### 7. config.py
- **Why last**: Largest, most complex
- **Commands**: 20
- **Estimated time**: 5 hours
- **Risk**: High

## Common Issues and Solutions

### Issue: Import Errors

**Problem**: `ImportError: cannot import name 'show_success_panel'`

**Solution**: Check import path
```python
# Wrong
from TimeLocker.cli.helpers import show_success_panel

# Right (from within cli package)
from ..helpers import show_success_panel
```

### Issue: Circular Imports

**Problem**: `ImportError: cannot import name 'app'`

**Solution**: Don't import `app` in command modules. Register in `__init__.py` instead.

### Issue: Missing Dependencies

**Problem**: Command uses helper not imported

**Solution**: Add to imports
```python
from ..helpers import (
    show_success_panel,
    show_error_panel,
    setup_logging,
    _get_service_manager_for_command,  # Add this
)
```

### Issue: Tests Fail

**Problem**: Tests can't find commands

**Solution**: Ensure commands are registered in `__init__.py`
```python
# cli/__init__.py
from .commands import targets_app
app.add_typer(targets_app, name="targets")
```

## Testing Checklist

For each extracted module:

- [ ] Module imports without errors
- [ ] All commands appear in `--help`
- [ ] Each command runs without errors
- [ ] All existing tests pass
- [ ] No diagnostic errors
- [ ] Documentation updated

## Verification Commands

```bash
# Check imports
python -c "from TimeLocker.cli.commands.targets import targets_app; print('OK')"

# Check CLI structure
timelocker --help | grep -A 20 "Commands:"

# Run specific command group tests
pytest tests/test_cli.py::test_targets_list -v

# Check for diagnostic errors
# (Use IDE or linter)

# Verify no regressions
pytest tests/test_cli.py -v --tb=short
```

## Success Criteria

Phase 2 is complete when:

✅ All 67 commands extracted to 7 modules  
✅ All tests passing  
✅ No diagnostic errors  
✅ CLI behavior unchanged  
✅ Documentation updated  
✅ Code review approved  

## Next Steps After Phase 2

1. Remove commented code from `cli.py`
2. Create `app.py` with Typer setup
3. Update documentation
4. Begin Phase 3: Pattern consolidation

## Resources

- [Phase 1 Implementation](../../updates/2025-11-07-093135-cli-refactoring-phase1.md)
- [CLI Refactoring Plan](./cli-refactoring-plan.md)
- [CLI Module README](../../src/TimeLocker/cli/README.md)

## Questions?

If you encounter issues:

1. Check this guide's "Common Issues" section
2. Review Phase 1 implementation for patterns
3. Consult the CLI Module README
4. Ask for help with specific error messages