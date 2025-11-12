# CLI Completion Fix Summary

**Date**: 2025-11-12  
**Type**: Bug Fix  
**Status**: Completed  
**Related Task**: Task 14 - Update backup CLI commands to use data selections

## Issue

The `complete_selection_names()` function in `src/TimeLocker/completion.py` was not finding existing selection templates because it was looking in the wrong directory.

### Root Cause

The function was looking for selections in:
```
~/.config/timelocker/data/selections/selections.json
```

But selection templates are actually stored in:
```
~/.local/share/timelocker/templates/*.json
```

This is because `SelectionTemplateManager` uses XDG_DATA_HOME for template storage, not XDG_CONFIG_HOME.

## Solution

Updated `complete_selection_names()` to:

1. **Use correct XDG path**: Read from `~/.local/share/timelocker/templates/` (XDG_DATA_HOME)
2. **Read template files directly**: Iterate through `*.json` files in the templates directory
3. **Extract names from JSON**: Parse each template file and extract the `name` field
4. **Handle errors gracefully**: Skip corrupted or invalid template files without crashing

### Code Changes

```python
@suppress_logging_for_completion
def complete_selection_names(incomplete: str) -> List[str]:
    """Complete data selection template names from configuration."""
    try:
        # Templates are stored in XDG_DATA_HOME/timelocker/templates
        xdg_data_home = os.environ.get('XDG_DATA_HOME')
        if xdg_data_home:
            data_dir = Path(xdg_data_home) / "timelocker"
        else:
            data_dir = Path.home() / ".local" / "share" / "timelocker"
        
        templates_dir = data_dir / "templates"
        
        if not templates_dir.exists():
            return []
        
        # List all template files and extract names
        template_names = []
        for template_file in templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                    if 'name' in template_data:
                        template_names.append(template_data['name'])
            except Exception:
                continue
        
        return [name for name in template_names if name.startswith(incomplete)]
    except Exception:
        return []
```

## Testing

### Manual Testing

```bash
# Test with existing selection
$ python -c "from src.TimeLocker.completion import complete_selection_names; print(complete_selection_names(''))"
['temporary-files']

# Test with prefix
$ python -c "from src.TimeLocker.completion import complete_selection_names; print(complete_selection_names('temp'))"
['temporary-files']
```

### Automated Testing

Created comprehensive test suite in `tests/TimeLocker/cli/test_completion.py`:

- ✅ Test completion returns list
- ✅ Test completion filters by prefix
- ✅ Test completion handles empty prefix
- ✅ Test completion handles nonexistent prefix
- ✅ Test completion returns no duplicates
- ✅ Test completion handles errors gracefully
- ✅ Test completion handles missing directory
- ✅ Test completer functions match underlying functions

**Test Results**: 17 passed in 0.21s

## Impact

### Before Fix
- Tab completion for `--selection` parameter did not work
- Users had to manually type selection template names
- No feedback on available selection templates

### After Fix
- Tab completion works correctly for selection templates
- Users can see all available templates by pressing Tab
- Completion filters as user types
- Consistent with repository completion behavior

## Verification

To verify the fix works:

```bash
# 1. Create a test selection
tl selections create test-sel --paths /tmp/test

# 2. Test completion in shell (bash/zsh)
tl backup create --selection <TAB>
# Should show: test-sel, temporary-files, etc.

# 3. Test with prefix
tl backup create --selection temp<TAB>
# Should complete to: temporary-files
```

## Related Changes

This fix was discovered and implemented as part of Task 14 (Update backup CLI commands to use data selections), which required verifying that completion functions work correctly for the new selection-based backup flow.

## Files Modified

- `src/TimeLocker/completion.py` - Fixed `complete_selection_names()` function
- `tests/TimeLocker/cli/test_completion.py` - Added comprehensive completion tests (new file)

## Future Improvements

1. **Cache template names**: Avoid reading files on every completion request
2. **Watch for changes**: Invalidate cache when templates directory changes
3. **Fuzzy matching**: Support approximate matches for better UX
4. **Template metadata**: Show descriptions in completion hints (if shell supports it)

---

**Rules Consulted**: coding-standards.md, testing-conventions.md  
**Rules Applied**: Error handling, comprehensive testing, documentation as code  
**Overrides**: None
