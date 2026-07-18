---
title: Repository review skill traceability
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
| T001 | Requirement 1-4 | Requirement 3 AC1; Requirement 4 AC2 | Overview; High-Level Design | package authority | lifecycle lint and readiness | none | none |
| T002 | Requirement 1-4 | Requirement 1 AC1; Requirement 1 AC2; Requirement 2 AC1; Requirement 2 AC2; Requirement 2 AC3; Requirement 3 AC1; Requirement 3 AC2; Requirement 3 AC3; Requirement 4 AC1 | Components; Low-Level Design | add skill; clarify routing | implementation review | skill package; `AGENTS.md` | none |
| T003 | Requirement 2, Requirement 4 | Requirement 2 AC1; Requirement 2 AC2; Requirement 2 AC3; Requirement 4 AC2 | Validation Strategy; Error Handling | validate skill | skill, Markdown, exercise, and Git checks | skill package | none |
| T004 | Requirement 3, Requirement 4 | Requirement 3 AC1; Requirement 3 AC2; Requirement 3 AC3; Requirement 4 AC1; Requirement 4 AC2 | Operational Considerations; Validation Strategy | promotion and closure | lifecycle and Spec 001 checks | skill; routing; history | none |

## Requirement To Delivery Matrix

| Requirement | Acceptance Criteria | Design Sections | Tasks | Verification | Durable Targets |
|-------------|---------------------|-----------------|-------|--------------|-----------------|
| Requirement 1 | Requirement 1 AC1; Requirement 1 AC2 | Expert Panel Reference | T001-T003 | role and synthesis exercise | `references/expert-panel.md` |
| Requirement 2 | Requirement 2 AC1; Requirement 2 AC2; Requirement 2 AC3 | Review Contract Reference | T002-T003 | schema and evidence exercise | `references/review-contract.md` |
| Requirement 3 | Requirement 3 AC1; Requirement 3 AC2; Requirement 3 AC3 | Skill Workflow; Operational Considerations | T001-T004 | read-only and authority checks | `SKILL.md`; `AGENTS.md` |
| Requirement 4 | Requirement 4 AC1; Requirement 4 AC2 | Discovery Metadata; Validation Strategy | T002-T004 | validator, metadata, lifecycle checks | skill metadata; history |

## Design To Implementation Matrix

| Design Section | Requirements | Tasks | Interfaces Or Files | Verification |
|----------------|--------------|-------|---------------------|--------------|
| Skill Workflow | Requirement 2, Requirement 3 | T002-T003 | `SKILL.md` | read-only bounded exercise |
| Expert Panel Reference | Requirement 1 | T002-T003 | `references/expert-panel.md` | role coverage and deduplication review |
| Review Contract Reference | Requirement 2 | T002-T003 | `references/review-contract.md` | schema and evidence review |
| Discovery Metadata | Requirement 4 | T002-T004 | `agents/openai.yaml`, `AGENTS.md` | skill validation and metadata inspection |
| Validation Strategy | Requirement 1-4 | T003-T004 | skill package and lifecycle artifacts | all planned checks |

## Correctness Property Coverage

| Property | Requirements | Tasks | Tests Or Verification | Residual Risk |
|----------|--------------|-------|-----------------------|---------------|
| CP-001 | Requirement 2 | T002-T003 | evidence-schema exercise | reviewer judgment |
| CP-002 | Requirement 1-2 | T002-T003 | deduplication exercise | semantic overlap |
| CP-003 | Requirement 3 | T002-T004 | Git status and read-only exercise | tool misuse outside skill |
| CP-004 | Requirement 3-4 | T001, T003-T004 | Spec 001 diff and readiness | none expected |

## Open Decision Impact

| Decision ID | Blocks | Affected Requirements | Affected Tasks | Resolution Needed |
|-------------|--------|-----------------------|----------------|-------------------|
| D001 | none | Requirement 4 | T002 | Resolved: use `.agents/skills/review-timelocker/`. |
| D002 | none | Requirement 1-3 | T002-T003 | Resolved: seven role-based passes work in one agent; subagents are optional. |
| D003 | none | Requirement 3-4 | T001-T004 | Resolved: Spec 006 may coexist without modifying Spec 001. |

## Maintenance Notes

- Update mappings if skill location, panel membership, or validation scope changes.
- Keep all acceptance criteria explicitly mapped before implementation continues.
