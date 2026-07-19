---
title: NPBackup migration parity requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
---

# Requirements

## Introduction

Preserve the observable backup semantics of the existing root-owned NPBackup
job before TimeLocker is installed or scheduled against its repository. This
package follows the machine-acceptance implementation committed by Spec 007 at
`433c0aa`; it does not authorize credential extraction, privileged
installation, release publication, or NPBackup cutover.

## Known Operator Baseline

- Root cron runs daily at 17:30.
- Active sources are `/home`, `/etc`, `/var`, `/srv`, `/root`, and `/nix/var`.
- The job requests maximum Restic compression, single-filesystem traversal,
  tag `Bruce-5560`, three configured patterns, and NPBackup built-in excludes.
- The repository URI, password, and AWS-compatible credentials are encrypted.
- Snapshot `8958659e` dated 2026-07-18 is the latest verified recent snapshot.

## Goals

- Carry compression and filesystem-boundary intent from CLI and schedules to
  the Restic invocation.
- Carry backup tags and exclusions through generated schedules.
- Preserve default behavior for existing callers and stored schedules.
- Establish a root-owned, credential-safe, observable migration sequence.

## Non-Goals

- Decrypting or copying NPBackup credentials without a separate secure choice.
- Installing or enabling a system service during Phase 1.
- Disabling or editing either NPBackup crontab during Phase 1.
- Applying destructive retention or prune operations during overlap.
- Publishing TimeLocker or closing Spec 007.

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/guides/user/recovery-operations-guide.md` | Current backup CLI and repository workflow | high | Add accepted execution options during promotion. |
| `docs/guides/developer/scheduling-guide.md` | Current schedule creation and rendering workflow | high | Add persisted parity fields during promotion. |
| Spec 007 verification at `433c0aa` | Machine-acceptance and executable-schedule baseline | high | Committed implementation dependency. |
| live masked NPBackup configuration and root cron, inspected 2026-07-19 | Current operator-job semantics | high | Sensitive values were not captured. |

## Requirements

### Requirement 1: Backup execution parity

**User story:** As the operator, I want explicit Restic execution options to
reach the backup engine so that a migrated job does not silently change its
filesystem or compression boundary.

**Priority:** must-have

### Acceptance Criteria

1. GIVEN compression `auto`, `off`, or `max`, WHEN `backup create` runs, THEN
   the selected value SHALL reach Restic as `--compression`.
2. IF an unsupported compression value is supplied, THEN TimeLocker SHALL fail
   before repository mutation with an actionable validation error.
3. GIVEN `--one-file-system`, WHEN a backup runs, THEN Restic SHALL receive
   `--one-file-system`; existing callers without the option SHALL retain
   cross-filesystem behavior.
4. GIVEN tags and exclude patterns, WHEN the backup runs, THEN all values SHALL
   reach the existing tag and exclusion command path without credential output.
5. GIVEN reviewed exclusion files, cache-directory exclusion, and allowlisted
   Restic backend options, WHEN the migrated production backup runs, THEN those
   values SHALL reach Restic exactly and unsupported backend options SHALL fail
   before repository mutation.

### Requirement 2: Executable schedule parity

**User story:** As the operator, I want a stored schedule to retain execution
options so generated assets represent the reviewed migration contract.

**Priority:** must-have

### Acceptance Criteria

1. Schedule create/edit SHALL persist repeatable tags and exclusions,
   compression, and the one-filesystem flag.
2. Cron, systemd, and Windows renderers SHALL emit only current `backup create`
   options and preserve argument boundaries for spaces and metacharacters.
3. Existing schedules without new fields SHALL render with existing defaults.
4. Schedule show/list/test SHALL expose or validate the parity fields without
   displaying credential values.

### Requirement 3: Staged migration safety

**User story:** As the operator, I want migration actions separated by risk so
NPBackup remains a recoverable fallback until TimeLocker is observed.

**Priority:** must-have

### Acceptance Criteria

1. Phase 1 SHALL NOT install a service, change a crontab, or write plaintext
   repository credentials.
2. The production install SHALL use a committed artifact in a root-owned
   location rather than a mutable user pyenv checkout.
3. TimeLocker SHALL attach read-only and restore an existing snapshot before
   its first production-source backup.
4. NPBackup SHALL remain active until non-overlapping scheduled TimeLocker runs
   and a subsequent restore pass; cutover requires separate approval.

## Correctness Properties

- **CP-001:** Generated argv parses as the current CLI and preserves every
  reviewed parity value exactly once per supplied value.
- **CP-002:** Default callers produce no new Restic compression or
  one-filesystem arguments.
- **CP-003:** Invalid compression cannot reach repository execution.
- **CP-004:** Generated assets contain credential references only, never values.
- **CP-005:** Phase 1 leaves systemd, cron, NPBackup, and production credentials
  unchanged.
- **CP-006:** Production migration does not silently drop NPBackup exclusion
  files, cache-directory exclusion, or reviewed S3 storage-class intent.

## Success Criteria

- **SC-001:** Focused backup tests prove valid compression and filesystem
  boundary options reach Restic while defaults emit no new arguments.
- **SC-002:** Schedule create, edit, show, test, and platform render tests prove
  all parity fields survive storage and argument-safe rendering.
- **SC-003:** Phase 1 validation records no live scheduler, NPBackup, repository,
  or credential mutation.
