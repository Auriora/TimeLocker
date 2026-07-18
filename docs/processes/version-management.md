---
title: Version management and GitHub releases
doc_type: process
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Version Management And GitHub Releases

This document describes how to manage versions in the TimeLocker project using the automated version bumping system.

## Overview

TimeLocker uses [semantic versioning](https://semver.org/) with the format `MAJOR.MINOR.PATCH`:

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backwards compatible manner
- **PATCH**: Backwards compatible bug fixes

## Quick Start

### Show Current Version

```bash
# Activate virtual environment first
source .venv/bin/activate

# Show current version and check consistency
python scripts/bump_version.py show
```

### Bump Version (Most Common)

```bash
# Activate virtual environment first
source .venv/bin/activate

# Patch version (1.0.0 -> 1.0.1) - for bug fixes
python scripts/bump_version.py bump patch

# Minor version (1.0.0 -> 1.1.0) - for new features
python scripts/bump_version.py bump minor

# Major version (1.0.0 -> 2.0.0) - for breaking changes
python scripts/bump_version.py bump major
```

### Preview Changes (Dry Run)

```bash
# See what would happen without making changes
source .venv/bin/activate
python scripts/bump_version.py bump patch --dry-run
python scripts/bump_version.py bump minor --dry-run
python scripts/bump_version.py bump major --dry-run
```

## Detailed Usage

### Using the Python Script Directly

The version management is handled by `scripts/bump_version.py`:

```bash
# Activate virtual environment first
source .venv/bin/activate

# Show current version and check consistency
python scripts/bump_version.py show

# Bump versions with various options
python scripts/bump_version.py bump patch                    # Standard patch bump
python scripts/bump_version.py bump minor --dry-run          # Preview minor bump
python scripts/bump_version.py bump major --no-tag           # Bump without git tag
python scripts/bump_version.py bump patch --no-commit        # Bump without git commit
```

### Command Options

- `--dry-run`: Preview changes without modifying files
- `--no-commit`: Don't create a git commit
- `--no-tag`: Don't create a git tag

## What Happens During Version Bump

When you bump a version, the system automatically:

1. **Updates version numbers** in:
    - `pyproject.toml`
    - `src/TimeLocker/__init__.py`

2. **Creates a git commit** with message: `Bump version: 1.0.0 → 1.0.1`

3. **Creates a git tag** with format: `v1.0.1`

4. **Validates consistency** across all version files

## Configuration

Version management is configured in `.bumpversion.cfg`:

```ini
[bumpversion]
current_version = 1.0.0
commit = True
tag = True
tag_name = v{new_version}
message = Bump version: {current_version} → {new_version}

[bumpversion:file:pyproject.toml]
search = version = "{current_version}"
replace = version = "{new_version}"

[bumpversion:file:src/TimeLocker/__init__.py]
search = __version__ = "{current_version}"
replace = __version__ = "{new_version}"
```

## Best Practices

### Before Bumping Version

1. **Ensure clean git state**: Commit or stash all changes
2. **Run tests**: Make sure all tests pass
3. **Update CHANGELOG.md**: Document what changed
4. **Review changes**: Use dry-run to preview

### Version Bump Guidelines

- **Patch (1.0.0 → 1.0.1)**: Bug fixes, documentation updates, minor improvements
- **Minor (1.0.0 → 1.1.0)**: New features, new CLI commands, backwards-compatible changes
- **Major (1.0.0 → 2.0.0)**: Breaking API changes, removed features, incompatible changes

### After Version Bump

1. **Push the version commit and tag**: `git push && git push --tags`
2. **Observe the release workflow**: The tag-triggered workflow verifies the
   tag against both Python version sources, runs the configured test suite,
   builds the source and wheel distributions, installs and smokes the wheel,
   uploads artifacts, and creates the GitHub release.
3. **Verify release artifacts**: Download the wheel/source distribution from
   the GitHub release and confirm its version and checksums before announcing it.
4. **Update documentation**: If needed for new features.
5. **Notify users**: For major changes.

The workflow does not publish to PyPI. Adding a package-registry publishing
step requires separate approval, credentials, and release-process updates.

## Troubleshooting

### Git Repository Not Clean

If you see "Git working directory is not clean":

```bash
# Check what files are modified
git status

# Either commit the changes
git add .
git commit -m "Prepare for version bump"

# Or use --allow-dirty (not recommended for actual releases)
python scripts/bump_version.py bump patch --dry-run  # This allows dirty for dry-run
```

### Version Inconsistency

If versions don't match across files:

```bash
# Check current state
python scripts/bump_version.py show

# Fix by doing a version bump (even if just patch)
python scripts/bump_version.py bump patch
```

### Permission Issues

Ensure you have write permissions to:

- Project files (`pyproject.toml`, `src/TimeLocker/__init__.py`)
- Git repository (for commits and tags)

## Integration With CI/CD

`.github/workflows/release.yml` is the durable executable release contract. It
runs only for semantic version tags matching `v*.*.*` and uses the repository's
Python metadata and test configuration. It does not move tags or mutate source.

## Manual Version Management

If you need to manually set a version:

1. Edit `.bumpversion.cfg` to set `current_version`
2. Edit `pyproject.toml` to set `version`
3. Edit `src/TimeLocker/__init__.py` to set `__version__`
4. Verify with `python scripts/bump_version.py show`

## Dependencies

The version management system requires:

- `bump2version` package (installed automatically)
- Git repository
- Python 3.12+

Install dependencies:

```bash
source .venv/bin/activate
pip install bump2version
```
