---
title: Operational best practices for AI agents
doc_type: guide
type: always_apply
name: Operational best practices for AI agents
priority: 40
scope: .*
description: Repository exploration, edit, evidence, and safety practices for TimeLocker agents.
cross_reference: [AGENT-GUIDE-Coding-Standards.md, AGENT-GUIDE-Planning-Protocol.md]
apply_when: always
owner: Auriora Team
status: active
last_reviewed: 2026-07-18
---

# Operational Best Practices for AI Agents

## Purpose

Define how agents gather current evidence, make bounded changes, and report
results in the TimeLocker repository.

## Operating Rules

- Start with repository-owned evidence: the current tree, `pyproject.toml`,
  durable docs, active specs, tests, Git state, and nearby implementation.
- Prefer the Python Agent IDE plugin and its MCP tools for repository context,
  impact analysis, diagnostics, documentation discovery, and test targeting.
  Narrow or retry partial calls and record limitations; use local tools when a
  required capability is unavailable.
- Use the Spec Lifecycle Manager for active spec discovery, reconciliation,
  task context, evidence, promotion, and closure. Do not implement from a task
  title without its requirements, design, traceability, and verification.
- Preserve unrelated working-tree changes. Keep edits minimal, review the diff,
  and use repository-relative paths in durable documentation.
- Prefer discovery over clarification when the answer is safely available in
  the repository. Ask before a material scope expansion or destructive action
  that is not already approved.
- Use non-interactive, repository-owned commands. Interpret complete output and
  distinguish new regressions from pre-existing limitations.
- Never expose credentials, repository passwords, tokens, callback codes, or
  sensitive command arguments in output, logs, tests, or documentation.
- Record durable current behavior in the appropriate documentation area.
  Record delivery evidence in an active spec, commit, pull request, CI run, or
  linked issue; do not create plans or update diaries under `docs/`.
- Validate in proportion to risk and report the exact commands, outcomes, and
  residual risks.

## Project Alignment

Code and documentation must remain consistent with current requirements under
`docs/1-requirements/`, architecture under `docs/2-architecture/`, and any
approved active spec. When these sources disagree, reconcile the conflict
before implementation.

## References

- [Coding Standards](./AGENT-GUIDE-Coding-Standards.md)
- [Planning Protocol](./AGENT-GUIDE-Planning-Protocol.md)
- [Documentation Conventions](./AGENT-RULE-Documentation-Conventions.md)
- [Active Specification Packages](../../specs/README.md)
