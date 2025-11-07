# Quick Start: Complete Phase 2

**Goal**: Extract remaining 60 commands using automation  
**Time**: 2-4 hours  
**Difficulty**: Easy (automated)

## Prerequisites

✅ Phase 1 complete (helpers extracted)  
✅ Phase 3 complete (patterns established)  
✅ 2 modules already extracted (targets, backup)

## Step-by-Step Guide

### Step 1: List Available Modules (30 seconds)

```bash
python scripts/extract_cli_commands.py --list
```

You should see 5 modules ready to extract:
- security (7 commands)
- credentials (8 commands)
- snapshots (10 commands)
- repositories (15 commands)
- config (20 commands)

### Step 2: Extract Security Module (5 minutes)

```bash
# Extract the module
python scripts/extract_cli_commands.py --module security

# Test the import
python -c "from TimeLocker.cli_modules.commands import security_app; print('✓ security imported')"

# Check for errors
python -m py_compile src/TimeLocker/cli_modules/commands/security.py
```

**Review the generated file**:
1. Open `src/TimeLocker/cli_modules/commands/security.py`
2. Look for `# TODO` comments
3. Add any missing imports

**Common imports to add**:
```python
from TimeLocker.security import SecurityService, AccessManager
from TimeLocker.completion import repository_completer
```

### Step 3: Extract Credentials Module (5 minutes)

```bash
# Extract
python scripts/extract_cli_commands.py --module credentials

# Test
python -c "from TimeLocker.cli_modules.commands import credentials_app; print('✓ credentials imported')"

# Check
python -m py_compile src/TimeLocker/cli_modules/commands/credentials.py
```

**Add missing imports** (if needed):
```python
from TimeLocker.security.credential_manager import CredentialManager
```

### Step 4: Extract Snapshots Module (10 minutes)

```bash
# Extract
python scripts/extract_cli_commands.py --module snapshots

# Test
python -c "from TimeLocker.cli_modules.commands import snapshots_app; print('✓ snapshots imported')"

# Check
python -m py_compile src/TimeLocker/cli_modules/commands/snapshots.py
```

**Add missing imports**:
```python
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.restore_manager import RestoreManager
from TimeLocker.completion import snapshot_id_completer
```

### Step 5: Extract Repositories Module (15 minutes)

```bash
# Extract
python scripts/extract_cli_commands.py --module repositories

# Test
python -c "from TimeLocker.cli_modules.commands import repos_app; print('✓ repositories imported')"

# Check
python -m py_compile src/TimeLocker/cli_modules/commands/repositories.py
```

**Add missing imports**:
```python
from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.services.repository_service import RepositoryService
from TimeLocker.completion import repository_name_completer
```

### Step 6: Extract Config Module (20 minutes)

```bash
# Extract
python scripts/extract_cli_commands.py --module config

# Test
python -c "from TimeLocker.cli_modules.commands import config_app; print('✓ config imported')"

# Check
python -m py_compile src/TimeLocker/cli_modules/commands/config.py
```

**Add missing imports**:
```python
from TimeLocker.config import ConfigurationValidator
from TimeLocker.config.configuration_backup_manager import ConfigurationBackupManager
from TimeLocker.importers.timeshift_importer import TimeshiftConfigParser
```

### Step 7: Run All Diagnostics (5 minutes)

```bash
# Check all new modules
for module in security credentials snapshots repositories config; do
    echo "Checking $module..."
    python -m py_compile src/TimeLocker/cli_modules/commands/$module.py
done
```

### Step 8: Test Imports (2 minutes)

```bash
# Test all imports work
python -c "
from TimeLocker.cli_modules.commands import (
    security_app,
    credentials_app,
    snapshots_app,
    repos_app,
    config_app
)
print('✓ All modules imported successfully')
"
```

### Step 9: Update Documentation (10 minutes)

Update `docs/REFACTORING-STATUS.md`:

```markdown
### Phase 2: Command Extraction (100% Complete) ✅

- ✅ targets.py (5 commands, 330 lines)
- ✅ backup.py (2 commands, 420 lines)
- ✅ security.py (7 commands, ~300 lines)
- ✅ credentials.py (8 commands, ~400 lines)
- ✅ snapshots.py (10 commands, ~800 lines)
- ✅ repositories.py (15 commands, ~1,200 lines)
- ✅ config.py (20 commands, ~1,500 lines)

**Total**: 67 commands, ~4,950 lines extracted
```

### Step 10: Celebrate! 🎉

You've completed Phase 2! All commands are now modularized.

## Alternative: Extract All at Once

If you're confident, extract all modules at once:

```bash
# Extract all modules
python scripts/extract_cli_commands.py --module all

# This will extract all 5 remaining modules in one go
# Takes about 1-2 minutes
```

Then review each module and add missing imports.

## Troubleshooting

### Import Error: "cannot import name 'X'"

**Solution**: Add the missing import to the generated module.

Look at the error message to see what's missing, then add:
```python
from TimeLocker.X import Y
```

### Syntax Error in Generated File

**Solution**: Review the generated file around the error line.

The script might have incorrectly detected function boundaries. Manually fix the code.

### Command Not Found After Extraction

**Solution**: Check that the module is imported in `commands/__init__.py`:

```python
from .security import security_app
__all__ = [..., "security_app"]
```

### "No commands found for X_app"

**Solution**: Check the app name in the script's MODULES dictionary matches cli.py.

## Verification Checklist

After extraction, verify:

- [ ] All 5 modules created
- [ ] All modules import without errors
- [ ] No diagnostic errors
- [ ] commands/__init__.py updated
- [ ] Documentation updated
- [ ] Git commit created

## Next Steps After Phase 2

1. **Run Full Test Suite**
   ```bash
   pytest tests/test_cli.py -v
   ```

2. **Apply Phase 3 to Existing Modules**
   - Refactor targets.py using base.py patterns
   - Refactor backup.py using base.py patterns

3. **Consider Phase 4** (Optional)
   - Service layer consolidation
   - Additional refactoring opportunities

## Time Estimate

| Task | Time |
|------|------|
| Extract security | 5 min |
| Extract credentials | 5 min |
| Extract snapshots | 10 min |
| Extract repositories | 15 min |
| Extract config | 20 min |
| Add missing imports | 30 min |
| Run diagnostics | 5 min |
| Test imports | 2 min |
| Update docs | 10 min |
| **Total** | **~2 hours** |

With the automation script, Phase 2 can be completed in about 2 hours instead of 2-3 days!

## Success Criteria

Phase 2 is complete when:

✅ All 67 commands extracted  
✅ All 7 command modules created  
✅ Zero diagnostic errors  
✅ All imports working  
✅ Documentation updated  

## Support

If you encounter issues:
1. Check `scripts/README.md` for detailed script documentation
2. Review `docs/guides/phase2-completion-plan.md` for manual approach
3. Look at existing modules (targets.py, backup.py) for examples
4. Check `src/TimeLocker/cli_modules/commands/base.py` for patterns

---

**Ready to start?** Run the first command:
```bash
python scripts/extract_cli_commands.py --module security
```
