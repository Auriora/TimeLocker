---
title: Adopt Spec Lifecycle Manager design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Technical Design

## Overview

Introduce a repository-native lifecycle index and governance contract, migrate
the single live legacy plan into a full package, and retain old plan files as
history. The external plugin remains the tooling authority; this repository
stores only project-specific lifecycle state.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| Requirement 1 | AC1-AC3 | Specs index and governance authority boundaries | Link review and lifecycle scan |
| Requirement 2 | AC1-AC3 | Active-plan migration and legacy plans index | Inventory and evidence review |
| Requirement 3 | AC1-AC2 | Closure log, archive index, and verification contract | Archive-index and closure checks |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | Legacy plan is superseded by exactly one new package. | Search active plans and specs. | GitHub issues remain trackers, not duplicate specs. |
| CP-002 | Verification requires durable promotion status before closure. | Lifecycle closure check. | Spec 000 remains active until committed and closed. |
| CP-003 | Completed CLI tasks carry `[x]` plus dated update evidence. | Task-state and evidence audit. | No completed plan is migrated. |

## High-Level Design

### System Architecture

```text
GitHub issues (assignment/state)
        |
        v
docs/specs (active delivery contract) ---> code/tests/config
        |                                      |
        +------------ verification ------------+
        |
        v
durable docs + docs/updates + docs/history
```

### Components and Changes

- `docs/specs/README.md`: lifecycle entry point and authority boundaries.
- Spec 000: evidence-bearing adoption package.
- Spec 001: migrated CLI consolidation contract.
- Agent rules and documentation indexes: route future work through lifecycle
  triage.
- History files: closure evidence and archive discovery.

### Data Models

No runtime data changes. Spec packages use YAML frontmatter, EARS-style
acceptance criteria, Kiro-style task markers, and Markdown traceability tables.

### Data Flow

An agent scans active specs, selects the next dependency-ready task, loads its
requirements/design/impact/verification context, executes it, records evidence,
promotes accepted behavior, and closes the package through the history files.

## Low-Level Design

### Algorithms and Logic

```text
triage(request):
    load repository rules and durable context
    scan active specs
    if change is complex or governance-sensitive:
        create or reconcile a spec package
        obtain approval before implementation
    else:
        execute the bounded change directly
    validate, promote durable truth, and log the update
```

### Function Signatures and Interfaces

The primary interface is the Spec Lifecycle Manager MCP toolset: scan,
readiness, task context, validation planning, promotion planning, and closure.
No repository-local executable interface is introduced.

### Error Handling

Missing artifacts, ambiguous active specs, incomplete evidence, or closure-only
content are blocking lifecycle diagnostics. Tool unavailability is recorded and
may fall back to the plugin's documented scripts without copying them here.

### Security, Trust, and Access

The migration changes documentation only. Existing repository permissions and
agent approval requirements remain in force; the lifecycle does not expand
write, network, or deployment authority.

### Migration and Compatibility

The old active plan is retained with `superseded` status and a link to Spec 001.
Completed and already-superseded plans remain unchanged. Existing inbound links
continue to resolve, while active links move to the new package.

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Package lint and scan | Requirements 1-3 | `verification.md` | Plugin-version differences |
| Task-state/evidence audit | Requirement 2, CP-003 | `verification.md` | Historic evidence is documentary |
| Archive-index check | Requirement 3 | `verification.md` | Cleanup commit remains pending until closure |
| Link and whitespace checks | Requirements 1-2 | `verification.md` | External GitHub state may drift |

## Downstream Task Guidance

- Required checkpoints before implementation: explicit user approval (received 2026-07-18).
- Properties needing task coverage: CP-001 through CP-003.
- Optional artifacts needed: change impact, verification, and traceability.
- Downstream review: reconcile package diagnostics after all edits.

## Operational Considerations

No deployment or rollback is needed. Reverting the documentation change restores
the prior workflow. Spec 000 cannot be removed until its final state is
committed and closure evidence is recorded.

## Open Questions

- None blocking implementation.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
