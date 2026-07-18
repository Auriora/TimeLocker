---
title: Prune historical documentation design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Technical Design

## Overview

The cleanup treats Git commits as the archival store and keeps only compact
lifecycle indexes in `docs/history/`. Historical collections are deleted rather
than moved. Current documents are edited in place to remove legacy sources,
future-only claims, and references to deleted files.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| Requirement 1 | AC1-AC3 | Category deletion manifest plus retained-surface allowlist | File inventory and active-spec scan |
| Requirement 2 | AC1-AC3 | Final-spec commits plus closure/index rows | Git log and `archive_index` |
| Requirement 3 | AC1-AC3 | Reference rewrite and current-state consolidation | `rg`, link checker, Agent Workbench Markdown checks |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | History indexes contain compact commit evidence only | Review history files and deleted-path searches | No live historical source links from front-door docs. |
| CP-002 | Explicit retained-surface allowlist includes Spec 001 and current docs | `scan_specs` and file inventory | Runtime code is out of scope. |
| CP-003 | Commit `c84dc3a` preserves Spec 000; Spec 002 receives its own final commit before removal | Git log and closure records | Deletions are recoverable with Git. |

## High-Level Design

### Deletion Categories

- All dated `docs/updates/` records; remove the update index and policy.
- All legacy `docs/plans/` plans and templates.
- Visible `docs/archive/`, point-in-time `docs/reports/`, local `docs/issues/`,
  legacy `docs/traceability/`, and obsolete project/test snapshots.
- Future-only REST API/OpenAPI/database/roadmap design assets.
- Completed Spec 000 after final commit evidence exists.

### Retained Surface

- `docs/README.md` as a lean current-state hub.
- Current architecture, implementation, testing how-to, user/developer/agent
  guides, processes, references, and active Spec 001.
- `docs/history/spec-closure-log.md` and `spec-archive-index.md`.
- Templates only for retained document classes.

### Reference Rewrite

Search retained files for `.kiro/specs`, deleted path families, v1.0 release
claims, orphaned requirement IDs, and references to removed future designs.
Delete purely historical references; replace lasting context with current code,
current durable docs, active Spec 001, Git commits, or GitHub issues.

## Low-Level Design

### Deletion Algorithm

```text
resolve exact tracked targets
exclude active Spec 001 and compact history indexes
delete targets through apply_patch
search retained tree for deleted paths and legacy sources
rewrite current docs and indexes
validate inventory, links, lifecycle, and formatting
commit complete Spec 002 package
remove closed spec packages and record closure breadcrumbs
```

### Error Handling

- Stop if a deletion target is outside the approved documentation categories.
- Preserve a file when it contains unique accepted current behavior until that
  behavior is promoted elsewhere.
- Treat broken incoming links as blockers until rewritten or explicitly proven
  to be pre-existing and out of scope.

### Security, Trust, and Access

No secrets, external services, or runtime state are involved. Git provides the
rollback and recovery boundary.

### Migration and Compatibility

Visible URLs for historical docs will disappear. This is intentional; current
navigation and lifecycle indexes replace them. Git history remains compatible
with forensic or audit recovery.

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Lifecycle scan/lint/closure/history checks | Requirements 1-2 | `verification.md` | none |
| Retained-tree `rg` searches | Requirement 3, CP-001 | task evidence | wording variants may require manual review |
| Link and Markdown checks | Requirement 3 AC3 | `verification.md` | pre-existing unrelated defects recorded separately |
| Git diff/status/log review | CP-002, CP-003 | `verification.md` | none |

## Downstream Task Guidance

- Required checkpoints before implementation: final Spec 000 commit `c84dc3a` exists; user approved the full cleanup.
- Properties or acceptance criteria needing explicit task coverage: CP-001 through CP-003.
- Optional artifacts needed before implementation: none beyond this package.
- Downstream review needed if this design changes after tasks are drafted: traceability and verification.

## Operational Considerations

The cleanup affects documentation discoverability only. Rollback is a Git
revert or restoration from the recorded final-spec/history commits.

## Open Questions

- None. The user explicitly approved the previously enumerated cleanup scope.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
