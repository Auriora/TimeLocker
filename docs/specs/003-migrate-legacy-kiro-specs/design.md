---
title: Migrate legacy Kiro specifications design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Technical Design

## Overview

Use an evidence-first disposition matrix rather than a directory-for-directory
copy. Completed and stale packages are closed into Git-backed history, deferred
proposals remain inactive, and only verified unfinished work receives a new
numbered lifecycle package.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| Requirement 1 | AC1-AC3 | Inventory and reconciliation matrix | Direct reads, file/test searches, focused tests where needed |
| Requirement 2 | AC1-AC3 | Selective package creation | Lifecycle lint, readiness, active-spec scan |
| Requirement 3 | AC1-AC3 | Promotion, removal, and closure sequence | Link scan, archive check, Git evidence |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | One disposition row per source package | Count and uniqueness check | Includes two deferred packages. |
| CP-002 | Active-package creation requires verified current work | Review disposition evidence | Unchecked legacy boxes are insufficient. |
| CP-003 | New package cites current files/tests/docs | Lifecycle readiness and traceability | |
| CP-004 | Durable promotion precedes source removal | Change-impact and closure review | |

## High-Level Design

### System Architecture

```text
.kiro/specs package
        |
        v
current evidence reconciliation
   | completed/stale/superseded -> Git-backed closure history
   | deferred/unapproved        -> inactive Git recovery pointer
   | verified active work       -> docs/specs/[###-slug]/
        |
        v
remove .kiro/specs and validate one lifecycle
```

### Components and Changes

- **Disposition matrix:** records one outcome and evidence basis per legacy package.
- **Lifecycle package generator:** manually adapts fallback templates only for verified active work.
- **Durable promotion pass:** ensures implemented behavior is represented in current docs.
- **Closure pass:** removes the legacy tree and records compact recovery breadcrumbs.

### Data Models

Each disposition contains package ID, legacy task state, current evidence,
classification, destination, and residual risk. No runtime schema changes.

### Data Flow

Read legacy requirements/design/tasks, compare them with current durable docs,
code, tests, and Spec 001, choose one disposition, then either create a current
package or close the source. Validation runs before source removal and again
after cleanup.

## Low-Level Design

### Algorithms and Logic

```text
for each legacy package:
    inspect all package artifacts
    identify checked, unchecked, optional, and deferred scope
    verify uncertain scope against current repository evidence
    assign exactly one disposition
    if verified active:
        create the smallest lifecycle package
    else:
        record recovery and closure routing
verify durable promotion
remove the legacy tree
validate active specs, history, links, and Git state
```

### Function Signatures and Interfaces

No runtime interfaces. The package contract is the Spec Lifecycle Manager
requirements/design/tasks format plus optional impact, verification, and
traceability artifacts.

### Error Handling

Ambiguous or contradictory evidence produces an unresolved disposition and
blocks removal of that package. Failed tests do not automatically reactivate an
old remediation plan; they require a current, bounded problem statement.

### Security, Trust, and Access

The migration reads hidden tracked files but does not handle credentials,
network secrets, or production systems. External issue creation and runtime
implementation remain out of scope.

### Migration and Compatibility

Git preserves original paths. Spec 001 remains authoritative for CLI
consolidation. Existing durable docs remain current-state sources and must not
link back to removed legacy packages.

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Legacy inventory and disposition count | Requirement 1, CP-001 | `verification.md`, T001-T002 | none |
| Focused code/test/doc evidence | Requirement 1-2, CP-002-CP-004 | task evidence | stale semantic claims require review |
| Lifecycle lint/readiness/scan | Requirement 2-3 | `verification.md` | none |
| Link, legacy-target, and Git checks | Requirement 3 | `verification.md` | external historic URLs may remain broken |

## Downstream Task Guidance

- Required checkpoints before implementation: disposition matrix and active-candidate decision.
- Properties or acceptance criteria that need explicit task coverage: CP-001 through CP-004.
- Optional artifacts needed before implementation: change impact, verification, traceability.
- Downstream review needed if this design changes after tasks are drafted: tasks and traceability.

## Operational Considerations

Commit the final migrated packages and Spec 003 state before deleting legacy
sources. Removal is recoverable with Git. Empty legacy directories must also be
removed so scanners do not report phantom packages.

## Open Questions

None. The user approved selective migration: only verified active work remains
under `docs/specs/`.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
