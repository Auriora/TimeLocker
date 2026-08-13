# Repository Automation Scripts

This directory contains reviewed repository automation and validation scripts.

## T011 Linux Deployment

`deploy_t011_linux.py` is the repository-owned privileged deployment harness
for Spec 010 T011. It:

- copies the exact wheel and release manifest into root-owned private evidence
  before validating or installing them;
- runs candidate CLI, backend, authorized-event, denied-event, systemd, and
  timer preflights before changing the service unit or release selector;
- uses inline identity probes, so restrictive umasks cannot make temporary
  probe files unreadable to their intended identities;
- selects the candidate with an expected-current compare-and-swap guard; and
- restores the prior selector and service unit after an exception, interrupt,
  termination, or failed post-activation check.

The harness does not run backup or retention. Its arguments must identify a
committed, freshly built release, and protected execution remains explicitly
approval-gated by the active spec.

Use `python scripts/deploy_t011_linux.py --help` to inspect its required,
hash-bound inputs. Do not copy it to `/tmp` or replace its inline probes with
external temporary scripts.

## CLI Extraction

## extract_cli_commands.py

Automates the extraction of command groups from the monolithic `cli.py` into modular command files following Phase 3 patterns.

### Features

- ✅ Automatically finds all commands for a module
- ✅ Generates module with proper header and imports
- ✅ Applies Phase 3 decorators (@with_error_handling, @with_logging)
- ✅ Simplifies type annotations (VerboseOption, JsonOption, etc.)
- ✅ Updates commands/__init__.py automatically
- ✅ Provides detailed progress output

### Usage

#### List available modules

```bash
python scripts/extract_cli_commands.py --list
```

Output:
```
📋 Available modules for extraction:

  1. security
     App: security_app
     Description: Security management commands
     Estimated lines: ~300

  2. credentials
     App: credentials_app
     Description: Credential management commands
     Estimated lines: ~400
  ...
```

#### Extract a single module

```bash
python scripts/extract_cli_commands.py --module security
```

This will:
1. Find all `@security_app.command()` decorators in cli.py
2. Extract the complete command functions
3. Generate `src/TimeLocker/cli_modules/commands/security.py`
4. Add Phase 3 decorators
5. Simplify type annotations
6. Update `commands/__init__.py`

#### Extract all modules

```bash
python scripts/extract_cli_commands.py --module all
```

Extracts all remaining modules in priority order:
1. security (7 commands)
2. credentials (8 commands)
3. snapshots (10 commands)
4. repositories (15 commands)
5. config (20 commands)

#### Options

```bash
# Extract without Phase 3 patterns (not recommended)
python scripts/extract_cli_commands.py --module security --no-phase3

# Specify custom paths
python scripts/extract_cli_commands.py \
    --module security \
    --cli-file path/to/cli.py \
    --output-dir path/to/output
```

### Example Output

```
🚀 Starting extraction...
   CLI file: src/TimeLocker/cli.py
   Output dir: src/TimeLocker/cli_modules/commands
   Phase 3 patterns: enabled
   Modules: security

📦 Extracting module: security
   App name: security_app
   Description: Security management commands
   Finding commands...
   ✓ Found 7 commands
     - status (security_status)
     - logs (security_logs)
     - notifications (security_notifications)
     - sessions (security_sessions)
     - cleanup (security_cleanup)
     - config (security_config)
     - audit (security_audit)
   Creating src/TimeLocker/cli_modules/commands/security.py...
   ✓ Created src/TimeLocker/cli_modules/commands/security.py
   📊 7 commands, ~285 lines

📝 Updating src/TimeLocker/cli_modules/commands/__init__.py...
   ✓ Added 1 imports

✨ Extraction complete!
   ✓ 1/1 modules extracted

📝 Next steps:
   1. Review generated files in src/TimeLocker/cli_modules/commands
   2. Add missing imports (marked with TODO)
   3. Test imports:
      python -c "from TimeLocker.cli_modules.commands import security_app; print('✓ security')"
   4. Run diagnostics:
      # Check security.py
   5. Update REFACTORING-STATUS.md
```

### What the Script Does

#### 1. Command Detection

Finds all commands by looking for patterns like:
```python
@security_app.command("status")
def security_status(...):
```

#### 2. Code Extraction

Extracts the complete function including:
- Decorator
- Function signature
- Docstring
- Implementation
- Error handling

#### 3. Phase 3 Enhancement

Adds decorators:
```python
@security_app.command("status")
@with_error_handling("Security Status Error")  # ← Added
@with_logging                                   # ← Added
def security_status(verbose: VerboseOption = False):  # ← Simplified
    """Show security status."""
    # Implementation (no try/except needed!)
```

#### 4. Type Annotation Simplification

Before:
```python
verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False
```

After:
```python
verbose: VerboseOption = False
```

#### 5. Module Generation

Creates complete module with:
- Header and docstring
- All necessary imports
- Phase 3 base imports
- All commands with enhancements

### After Extraction

#### 1. Review Generated Files

Check the generated module for:
- Missing imports (marked with `# TODO`)
- Module-specific dependencies
- Any extraction issues

#### 2. Add Missing Imports

The script adds a TODO comment for module-specific imports:
```python
# Module-specific imports will be added as needed
# TODO: Review and add specific imports for this module
```

Add any required imports, for example:
```python
from TimeLocker.security import SecurityService, AccessManager
from TimeLocker.completion import repository_completer
```

#### 3. Test Imports

```bash
python -c "from TimeLocker.cli_modules.commands import security_app; print('✓ OK')"
```

#### 4. Run Diagnostics

Check for any errors:
```bash
# Using your IDE or
python -m py_compile src/TimeLocker/cli_modules/commands/security.py
```

#### 5. Test Commands

```bash
# Test help
timelocker security --help

# Test a command
timelocker security status
```

### Troubleshooting

#### "No commands found"

The script couldn't find commands for the specified app. Check:
- App name is correct in MODULES dictionary
- Commands exist in cli.py
- Decorator pattern matches: `@{app_name}.command("name")`

#### Import errors after extraction

Add missing imports to the generated file. Look for:
- Service classes (SecurityService, etc.)
- Completion functions
- Utility functions
- Exception classes

#### Commands not working

Check:
1. Module is imported in `commands/__init__.py`
2. App is registered in main cli.py (if needed)
3. All dependencies are imported
4. No syntax errors (run diagnostics)

### Advanced Usage

#### Custom Module Definition

Edit the `MODULES` dictionary in the script to add or modify modules:

```python
MODULES = {
    "mymodule": ModuleInfo(
        name="mymodule",
        app_name="mymodule_app",
        description="My custom module",
        commands=[],
        estimated_lines=500,
        priority=6
    ),
}
```

#### Batch Processing

Extract multiple specific modules:
```bash
for module in security credentials snapshots; do
    python scripts/extract_cli_commands.py --module $module
done
```

### Integration with Phase 2

This script is designed to complete Phase 2 of the CLI refactoring:

**Phase 2 Goal**: Extract all 67 commands into 7 modular files

**Script Contribution**:
- Automates extraction of 60 remaining commands
- Applies Phase 3 patterns automatically
- Reduces manual work from days to hours
- Ensures consistency across all modules

### Performance

- **Single module**: ~5-10 seconds
- **All modules**: ~30-60 seconds
- **Manual equivalent**: 1-2 days

### Limitations

1. **Import Detection**: Cannot automatically detect all required imports
2. **Complex Logic**: May need manual review for complex command logic
3. **Sub-commands**: May need special handling for nested command groups
4. **Custom Decorators**: Only adds standard Phase 3 decorators

### Best Practices

1. **Extract one module at a time** for first few modules
2. **Test after each extraction** to catch issues early
3. **Review generated code** before committing
4. **Update documentation** after extraction
5. **Run full test suite** after all extractions

### See Also

- `docs/guides/phase2-completion-plan.md` - Detailed completion strategy
- `docs/REFACTORING-STATUS.md` - Current refactoring status
- `src/TimeLocker/cli_modules/commands/base.py` - Phase 3 patterns
- `src/TimeLocker/cli_modules/commands/targets_refactored.py` - Example refactored module
