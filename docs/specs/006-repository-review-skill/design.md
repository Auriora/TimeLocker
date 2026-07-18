---
title: Repository review skill design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Technical Design

## Overview

Create `.agents/skills/review-timelocker/` as a concise repository-local skill.
The skill coordinates seven expert review stances, gathers authoritative
evidence, synthesizes duplicates, and returns findings before summaries.

## High-Level Design

```text
review request
  -> authority and scope preflight
  -> repository evidence collection
  -> seven role-based review passes
  -> deduplication and confidence check
  -> findings-first report and routing
```

Spec 006 may coexist with Spec 001 because it changes only `.agents/skills/`,
the active-spec index, and lifecycle evidence. It must not edit runtime code,
tests, configuration, or any Spec 001 artifact.

## Components

### Skill Workflow

`SKILL.md` defines scope classification, preflight, evidence collection, role
passes, synthesis, reporting, and remediation routing. It keeps review-only
requests read-only and distinguishes planned checks from executed evidence.

### Expert Panel Reference

`references/expert-panel.md` defines these roles:

1. project steward and operator advocate;
2. Restic and backup/recovery specialist;
3. Python CLI architect;
4. security and privacy reviewer;
5. reliability and test strategist;
6. operations and portability reviewer; and
7. documentation and lifecycle reviewer.

Each role has a bounded remit, source priorities, and characteristic failure
modes to reduce generic or overlapping commentary.

### Review Contract Reference

`references/review-contract.md` defines scope receipts, severity, confidence,
finding fields, deduplication, clean-review output, and routing. Stable finding
IDs use `TLR-###` within one review and are never renumbered during follow-up.

### Discovery Metadata

`agents/openai.yaml` provides a human-facing name, description, and a default
prompt that explicitly invokes `$review-timelocker`.

## Low-Level Design

- Initialize with the Skill Creator `init_skill.py` script and only the
  `references` resource directory.
- Keep `SKILL.md` below 500 lines and place detailed role and output definitions
  in one-level references.
- Require exact paths, symbols, lines, commands, or configuration values as
  evidence where available.
- Rank findings `critical`, `high`, `medium`, or `low`; use `note` for
  non-actionable context.
- Report confidence as `high`, `medium`, or `low` and explain low-confidence
  limitations.
- Do not manufacture findings to populate every role.

## Error Handling

- If an evidence provider is unavailable, continue with repository-local
  evidence and name the missing capability.
- If repository authorities conflict, report the conflict and stop before
  recommending implementation.
- If requested scope is too broad for complete evidence, return a bounded
  partial review with explicit coverage gaps.

## Operational Considerations

- The skill has no runtime dependency and invokes no external service.
- Multi-agent execution is optional and only allowed when user and platform
  instructions authorize it; the workflow works in a single agent.
- Review reports remain conversational, PR, issue, or user-requested artifacts;
  they are not added to `docs/` by default.
- Rollback is a Git revert of the skill and routing changes.

## Validation Strategy

- Validate the skill with Skill Creator `quick_validate.py`.
- Check Markdown structure and internal links.
- Run a bounded read-only exercise against known TimeLocker files and inspect
  its scope receipt and finding schema.
- Confirm Spec 001 files and T005 readiness are unchanged.
- Run lifecycle lint, readiness, evidence, promotion, and closure checks.

## Open Questions

None. The user approved the panel, repository-local placement, and Spec 006.

## Related Artifacts

- Requirements: `requirements.md`
- Tasks: `tasks.md`
- Change Impact: `change-impact.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
