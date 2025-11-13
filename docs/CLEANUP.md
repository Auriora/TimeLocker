# Quick Cleanup Guide

To clean your TimeLocker user environment and start fresh:

## One-Command Cleanup

```bash
./scripts/clean-user-environment.sh
```

This will remove all TimeLocker configuration, data, cache, and scripts from your user directories.

## What Gets Cleaned

- **Configuration**: `~/.config/timelocker/`
- **Data**: `~/.local/share/timelocker/`
- **State**: `~/.local/state/timelocker/`
- **Cache**: `~/.cache/timelocker/`
- **Legacy**: `~/.timelocker/`
- **Scripts**: `~/.local/bin/timelocker-*.sh`
- **Systemd services**: `~/.config/systemd/user/timelocker*`

## Verify Clean Environment

After cleanup:

```bash
tl repos list  # Should show no repositories
```

## Full Documentation

See [docs/guides/user-environment-cleanup.md](docs/guides/user-environment-cleanup.md) for detailed information.
