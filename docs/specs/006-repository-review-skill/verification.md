---
title: Repository review skill verification
doc_type: spec
artifact_type: verification
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Verification

## Quality Gates

| Gate | Status | Evidence |
|------|--------|----------|
| Requirements and design approved | pass | User approval on 2026-07-18. |
| Package lifecycle baseline | pass | Lint clean; every readiness gap count is 0. |
| Skill implementation | pass | Durable skill package and `AGENTS.md` routing exist. |
| Skill validation and exercise | pass | Validator, assertions, and read-only fingerprint check passed. |
| Durable promotion and closure | pending | T004. |

## Validation Plan

| Check | Pass signal | Covers |
|-------|-------------|--------|
| Skill Creator `quick_validate.py` | Exit 0 and valid metadata. | Requirement 4, SC-001 |
| Metadata inspection | Default prompt names `$review-timelocker`; fields match `SKILL.md`. | Requirement 4 |
| Read-only bounded exercise | Scope receipt and schema-complete evidence-based findings or clean result. | Requirement 1-3, SC-002 |
| Markdown and link checks | No blocking structure or broken-link findings. | SC-003 |
| Spec 001 comparison | No diff; T005 remains next and ready. | CP-004, SC-004 |
| Spec 006 lifecycle checks | No blocking lint, readiness, evidence, promotion, or closure findings. | SC-004 |
| `git diff --check` | Exit 0. | SC-003 |

## Evidence Log

| Date | Evidence | Result |
|------|----------|--------|
| 2026-07-18 | User approval recorded in `requirements.md` and `tasks.md`. | seven-role panel, local skill scope, and Spec 006 approved |
| 2026-07-18 | Skill Creator `quick_validate.py`; metadata and reference assertions. | pass |
| 2026-07-18 | Bounded contract exercise over the skill, routing, and active-spec index. | no actionable findings; Git status unchanged |
| 2026-07-18 | Agent Workbench `check_markdown_set` over eight visible documents. | 0 structure/link errors; 31 advisory table-readability warnings |
| 2026-07-18 | `python scripts/link_checker.py` and `git diff --check`. | pass; canonical-link suggestions only |

## Residual Risks

- Role-based review improves breadth but cannot guarantee defect discovery.
- A single-agent exercise cannot independently validate multi-agent orchestration;
  the skill therefore treats multi-agent execution as optional, not required.

## Promotion And Cleanup

- **Durable skill:** `.agents/skills/review-timelocker/`
- **Durable routing:** `AGENTS.md`
- **Cleanup action:** remove
- **Final active-state commit:** pending
- **Closure cleanup commit:** pending
- **Ready for closure:** no

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Change Impact: `change-impact.md`
- Traceability: `traceability.md`
