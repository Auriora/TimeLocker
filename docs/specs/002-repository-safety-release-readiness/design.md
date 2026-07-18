---
title: Repository safety and release readiness design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Technical Design

## Overview

This remediation carries overwrite policy through the restore abstraction,
replaces deterministic credential auto-unlock with explicit secret resolution,
normalizes test imports, replaces the release workflow, and promotes current
architecture truth into durable documents.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| R1 | AC1-AC3 | Explicit overwrite keyword from CLI/orchestrator through repository command | unit command tests and restore-manager tests |
| R2 | AC1-AC3 | Environment/password-file resolver with POSIX permission checks | focused security tests |
| R3 | AC1-AC3 | Source-install docs and Python tag workflow | YAML review, build, wheel smoke |
| R4 | AC1-AC2 | Mechanical import normalization plus repository guard | search and pytest |
| R5 | AC1-AC3 | Current-state rewrites | Markdown and link validation |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | `BackupRepository.restore(..., overwrite=...)` defaults to `never`; Restic command always emits the parameter | exact argv tests | Optional keyword preserves callers. |
| CP-002 | `auto_unlock()` consults only explicit operator inputs | fresh-manager tests with sanitized environment | No legacy deterministic fallback. |
| CP-003 | test sources contain only `TimeLocker` imports/patch targets | repository guard and full suite | Mechanical change only. |
| CP-004 | release job uses `pyproject.toml`, pytest, build, wheel, and `gh` | workflow inspection and local commands | No PyPI publication. |

## High-Level Design

### Components and Changes

- Restore contract: add a backward-compatible keyword-only overwrite mode and
  translate `ConflictResolution` to Restic's `never` or `always` values.
- Credential manager: resolve `TIMELOCKER_MASTER_PASSWORD` or
  `TIMELOCKER_MASTER_PASSWORD_FILE`; reject unsafe file metadata.
- Test suite: replace source-layout imports and add a namespace-policy test.
- Release pipeline: validate tag/version, test, build, install-smoke, upload,
  and create the GitHub release.
- Durable docs: describe only the implemented CLI/service/Restic architecture.

### Data Flow

Restore flow is CLI authorization -> `RestoreOptions` conflict policy ->
`BackupSnapshot.restore` -> repository `restore` -> Restic `--overwrite`.
Credential flow is explicit operator secret source -> key derivation -> store
decrypt; host identifiers never participate.

## Low-Level Design

### Function Signatures and Interfaces

```python
def restore(snapshot_id: str, target_path: Path | None = None,
            *, overwrite: str = "never") -> str: ...
```

The Restic adapter validates the overwrite value against `never` and `always`.
`CredentialManager.auto_unlock()` remains as a compatibility method but means
non-interactive unlock from explicit secret sources only.

### Error Handling

- Invalid overwrite modes raise `ValueError` before process execution.
- Missing or unsafe secret files log a safe category without secret contents
  and return `False` from non-interactive unlock.
- Existing stores encrypted with deterministic host keys are not silently
  opened; operators must re-enter and rotate affected repository credentials.

### Security, Trust, and Access

Secret-file paths are operator-controlled. The manager rejects symlinks and
non-regular files, and on POSIX requires no group/other permission bits. Secret
values are never logged. GitHub release automation receives only the standard
repository token and performs no package-registry publication.

### Migration and Compatibility

The optional restore keyword is backward compatible for existing callers.
Deterministically encrypted credential stores are intentionally not compatible
because retaining a host-derived fallback would preserve the critical defect.
The durable credential guide will call out re-entry and rotation.

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Focused restore/security tests | R1, R2 | `verification.md` | platform-specific file permissions |
| Namespace search and test guard | R4 | `verification.md` | non-Python references are informational |
| Build and wheel smoke | R3 | `verification.md` | GitHub release mutation only runs on a tag |
| Markdown/link checks | R5 | `verification.md` | none expected |
| Full configured pytest | all code changes | `verification.md` | excluded performance/stress policy as configured |

## Downstream Task Guidance

- Required checkpoints: complete focused tests before mechanical import rewrite;
  run full suite after all changes.
- All acceptance criteria and correctness properties map in `traceability.md`.
- No open decision blocks implementation.
- Reconcile design, traceability, and verification if behavior changes.

## Operational Considerations

Release creation remains tag-triggered and non-PyPI. Scheduled deployments must
provide a protected credential-store secret explicitly. Operators with legacy
auto-key stores should treat stored credentials as exposed and rotate them.

## Open Questions

- None blocking. PyPI publication remains a separately approved future change.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
