---
title: Prune historical documentation traceability
doc_type: spec
artifact_type: traceability
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Traceability Matrix

## Task To Context Matrix

| Task ID | Requirements | Acceptance Criteria | Design Sections | Change Impact | Verification | Durable Targets | Open Decisions |
|---------|--------------|---------------------|-----------------|---------------|--------------|-----------------|----------------|
| T001 | Requirement 1; Requirement 2; Requirement 3 | Requirement 1 AC1; Requirement 2 AC1; Requirement 3 AC1 | Deletion Categories; Retained Surface | Durable Source Mapping | Agent Readiness Evidence | Git history; `docs/history/` | none |
| T002 | Requirement 1; Requirement 2 | Requirement 1 AC1; Requirement 1 AC3; Requirement 2 AC1; Requirement 2 AC2; Requirement 2 AC3 | Deletion Categories; Deletion Algorithm | Proposed Changes | Quality Gates | agent rules; `docs/history/`; `docs/specs/README.md` | none |
| T003 | Requirement 1; Requirement 3 | Requirement 1 AC2; Requirement 3 AC1; Requirement 3 AC2 | Reference Rewrite | Promotion Targets | Requirement Coverage | docs hub/status; retained durable docs | none |
| T004 | Requirement 1; Requirement 2; Requirement 3 | Requirement 1 AC1; Requirement 1 AC2; Requirement 1 AC3; Requirement 2 AC1; Requirement 2 AC2; Requirement 2 AC3; Requirement 3 AC1; Requirement 3 AC2; Requirement 3 AC3 | Validation Strategy | Promotion Targets | Validation Commands | all retained docs | none |
| T005 | Requirement 2 | Requirement 2 AC1; Requirement 2 AC2; Requirement 2 AC3 | Migration and Compatibility | Promotion Targets | Durable Promotion And Cleanup | agent rules; specs README; history indexes | none |

## Requirement To Delivery Matrix

| Requirement | Acceptance Criteria | Design Sections | Tasks | Verification | Durable Targets |
|-------------|---------------------|-----------------|-------|--------------|-----------------|
| Requirement 1 | AC1-AC3 | Deletion Categories; Retained Surface | T001-T004 | inventory, links, lifecycle scan | `docs/README.md`; retained current docs |
| Requirement 2 | AC1-AC3 | Deletion Algorithm; Migration and Compatibility | T001, T002, T004, T005 | Git/history/closure checks | Git history; `docs/history/` |
| Requirement 3 | AC1-AC3 | Reference Rewrite; Validation Strategy | T001, T003, T004 | `rg`, link, Markdown checks | retained durable docs |

## Correctness Property Coverage

| Property | Requirements | Design Sections | Tasks | Tests Or Verification | Residual Risk |
|----------|--------------|-----------------|-------|-----------------------|---------------|
| CP-001 | Requirement 2; Requirement 3 | Reference Rewrite | T003-T004 | retained-tree search and link checks | wording variants manually reviewed |
| CP-002 | Requirement 1 | Retained Surface | T001-T004 | active spec scan and file inventory | none |
| CP-003 | Requirement 2 | Deletion Algorithm | T001, T002, T005 | Git log and closure records | none |

## Design To Implementation Matrix

| Design Section | Requirements | Tasks | Interfaces Or Files | Verification |
|----------------|--------------|-------|---------------------|--------------|
| Deletion Categories | Requirement 1; Requirement 2 | T001-T002 | historical docs paths | inventory and Git status |
| Retained Surface | Requirement 1 | T002-T004 | active/current docs | scan and direct review |
| Reference Rewrite | Requirement 3 | T003-T004 | retained Markdown/YAML | `rg`, link, Markdown checks |
| Validation Strategy | Requirement 1; Requirement 2; Requirement 3 | T004-T005 | lifecycle and repo tools | `verification.md` |

## Open Decision Impact

No open decisions. The user explicitly selected Git-backed history and approved
all enumerated deletion categories.
