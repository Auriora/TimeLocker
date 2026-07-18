---
title: Repository hygiene traceability matrix
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
| T001 | Requirement 4 | Requirement 4 AC1 | Files And Boundaries; Migration And Compatibility | Lifecycle sequencing | CP-003 | Spec 001 | none |
| T002 | Requirement 1 | Requirement 1 AC1, Requirement 1 AC2, Requirement 1 AC3 | Instruction Authority | Agent authority cleanup | Requirement 1; CP-001 | `AGENTS.md`, `docs/guides/ai-agent/` | none |
| T003 | Requirement 2 | Requirement 2 AC1, Requirement 2 AC2, Requirement 2 AC3 | Front Door And Resources | Front-door/resource changes | Requirement 2; CP-001, CP-002 | `README.md`, `CHANGELOG.md`, `docs/resources/` | none |
| T004 | Requirement 3 | Requirement 3 AC1, Requirement 3 AC2, Requirement 3 AC3 | Durable Documentation Shape | Template/investigation changes | Requirement 3; CP-001 | `docs/templates/`, current code/tests | none |
| T005 | Requirement 1, Requirement 2, Requirement 3, Requirement 4 | Requirement 1 AC1, Requirement 1 AC2, Requirement 1 AC3, Requirement 2 AC1, Requirement 2 AC2, Requirement 2 AC3, Requirement 3 AC1, Requirement 3 AC2, Requirement 3 AC3, Requirement 4 AC1, Requirement 4 AC2 | Validation Strategy | all | SC-001, SC-002, SC-003; CP-001, CP-002, CP-003 | `verification.md` | none |
| T006 | Requirement 4 | Requirement 4 AC2 | Migration And Compatibility | Lifecycle sequencing | CP-003 and closure gates | durable docs and lifecycle history | none |

## Requirement To Delivery Matrix

| Requirement | Acceptance Criteria | Design Sections | Tasks | Verification | Durable Targets |
|-------------|---------------------|-----------------|-------|--------------|-----------------|
| Requirement 1 | Requirement 1 AC1, Requirement 1 AC2, Requirement 1 AC3 | Instruction Authority | T002, T005, T006 | Requirement 1; CP-001 | `AGENTS.md`, agent guides |
| Requirement 2 | Requirement 2 AC1, Requirement 2 AC2, Requirement 2 AC3 | Front Door And Resources | T003, T005, T006 | Requirement 2; CP-001, CP-002 | README, changelog, docs resources |
| Requirement 3 | Requirement 3 AC1, Requirement 3 AC2, Requirement 3 AC3 | Durable Documentation Shape | T004, T005, T006 | Requirement 3; CP-001 | `docs/templates/`, code/tests |
| Requirement 4 | Requirement 4 AC1, Requirement 4 AC2 | Files And Boundaries; Migration And Compatibility | T001, T005, T006 | Requirement 4; CP-003 | Spec 001 and lifecycle history |

## Correctness Property Coverage

| Property | Requirements | Design Sections | Tasks | Tests Or Verification | Residual Risk |
|----------|--------------|-----------------|-------|-----------------------|---------------|
| CP-001 | Requirements 1-3 | all cleanup sections | T002-T005 | stale-path scan, link and Markdown checks | historical log wording reviewed manually |
| CP-002 | Requirement 2 | Front Door And Resources | T003, T005 | path existence and focused script checks | none expected |
| CP-003 | Requirement 4 | Migration And Compatibility | T001, T005, T006 | lifecycle readiness, audit, closure | none after closure |

## Design To Implementation Matrix

| Design Section | Requirements | Tasks | Interfaces Or Files | Verification |
|----------------|--------------|-------|---------------------|--------------|
| Instruction Authority | Requirement 1 | T002 | agent router, rules, steering | content and Markdown checks |
| Front Door And Resources | Requirement 2 | T003 | README, changelog, assets, scripts | link and focused path checks |
| Durable Documentation Shape | Requirement 3 | T004 | templates, investigation, empty dirs | inventory and focused tests |
| Migration And Compatibility | Requirement 4 | T001, T006 | Specs 001/004 and history | lifecycle checks |

## Open Decision Impact

| Decision ID | Blocks | Affected Requirements | Affected Tasks | Resolution Needed |
|-------------|--------|-----------------------|----------------|-------------------|
| none | none | none | none | All cleanup choices were approved on 2026-07-18. |

## Maintenance Notes

- Update mappings when task scope or durable destinations change.
- Do not close the package with accepted content remaining only in Spec 004.
