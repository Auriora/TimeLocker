---
title: Planning protocol
doc_type: guide
type:        "agent_requested"
name:        "Planning protocol"
priority:    30
scope:       "planning-flow"
description: "Use structured planning for complex, multi-file changes or feature work."
cross_reference: ["AGENT-GUIDE-General-Preferences.md"]
apply_when:   "task_type == \"complex_change\""
owner: Auriora Team
status: active
last_reviewed: 2026-07-18
---

# AI Agent Rule/Guide: Planning Protocol

- **Type**: agent_requested
- **Priority**: 30
- **Scope**: planning-flow
- **Description**: Use structured planning for complex, multi-file changes or feature work.
- **Cross-Reference**: AGENT-GUIDE-General-Preferences.md
- **Apply When**: task_type == "complex_change"

## 1. Purpose

This protocol combines the repository's explicit approval gate with the Spec
Lifecycle Manager. It distinguishes direct low-risk work from changes that need
requirements, design, evidence-bearing tasks, durable promotion, and closure.

## 2. Rule/Guideline Details

At task start, load the durable repository rules and scan `docs/specs/` through
the Spec Lifecycle Manager. Prefer its MCP tools for discovery, readiness, task
context, validation planning, promotion, and closure. Use repository-local or
plugin scripts only when the MCP capability is unavailable or for CI validation.

### 2.1. Triage

Classify the request before writing a plan:

- **Direct change**: narrow, low-risk work with clear acceptance and validation.
  It may proceed without a spec, subject to all other repository rules.
- **Spec-needed change**: multi-file feature, migration, architectural or
  cross-cutting refactor, governance change, or work with ambiguous acceptance,
  dependencies, promotion, or closure. Create or reconcile an active package
  under `docs/specs/[###-slug]/`.
- **Existing spec work**: resume the active package only after reconciling its
  requirements, design, tasks, implementation, durable docs, and evidence.

GitHub issues track assignment and issue state. Active specs govern delivery
scope, sequencing, acceptance criteria, and evidence. Durable docs describe
accepted current behavior. Commits, pull requests, CI artifacts, and issue
history provide chronological implementation evidence.

### 2.2. Desired Outcome

- Define the desired state with measurable success criteria (both functional and non-functional).
- For each criterion: state how it can be **measured or tested**.
- Limit: max **5 bullets**, max **100 words**.

### 2.3. Scope & Assumptions

- Restate the problem; define all key terms.
- Enumerate explicit & implied assumptions.
- Ask clarifying questions if any success criterion, constraint, or dependency is missing.
- Limit: ≤ **5 bullets**, ≤ **100 words**.

### 2.4. Spec Artifacts and Gap Plan

- Identify gaps between durable current state and the desired outcome.
- For spec-needed work, create or reconcile `requirements.md`, then `design.md`,
  then `tasks.md`. Add change impact, verification, traceability, research, or
  open decisions only when they reduce ambiguity.
- Tasks must use dependency-aware checkboxes and include acceptance and evidence.
- Propose a high-level plan (modules or steps) to bridge the gaps.
- Present in human-readable form: bullets or table. If a small reference block labeled "Structured reference" is included at the end, it must be clearly
  separated.
- Limit: ≤ 5 gaps, ≤ 5 plan steps, ≤ 150 words.

### 2.5. Risks

- List top risks in a table with columns: **Risk**, **If-then detector**, **Mitigation**.
- Limit to ≤ **5 risks**.
- Brief rationale: for each risk, 1-2 bullets explaining the likelihood & impact.

### 2.6. Tests and Verification

- Provide a checklist for applicable unit, integration, acceptance,
  documentation, and lifecycle checks. Each item needs a pass/fail criterion.
- Map spec validation to requirements, task IDs, risks, and evidence locations.
- Limit: ≤ **7 items** total.
- If tests depend on risk or assumptions, explicitly link.

### 2.7. Approval Gate

- Present the plan before implementation and stop with
  `<<AWAIT_CONFIRM: ...?>>`.
- Enter EXECUTE only after explicit user approval.
- Approval covers the described scope only. Re-plan and ask again before a
  material scope expansion or a newly discovered risky/destructive action.

### 2.8. Execute and Record Evidence

- Before implementation, load the selected task's full package context and mark
  it `[~]`.
- Execute in dependency order and complete a task only when its acceptance
  criteria and evidence are recorded.
- Reconcile drift whenever work resumes or implementation changes the design.
- Record substantial completed work in the active spec and its commits, pull
  request, CI artifacts, or linked issue as appropriate.

### 2.9. Promote and Close

- Promote accepted behavior, contracts, decisions, operations, and validation
  guidance into durable docs before closure.
- Run lifecycle lint, readiness, evidence, promotion, and closure checks.
- Commit the complete final spec state before removing or archiving a package.
- Record closure in `docs/history/spec-closure-log.md` and
  `docs/history/spec-archive-index.md`, then update active indexes.
- Do not close a package with unresolved accepted content that exists only in
  the spec; route deferred work to an issue or follow-up spec.

### 2.10. Deliverables

- Deliver the final plan and executive summary (mapping back to Desired Outcome).
- Restate any questions or assumptions in a structured reference block for confirmation.
- Limit: max **200 words** in summary.
- Reminder: upon completion, ensure the active spec and delivery records contain
  enough evidence to reproduce the acceptance decision.

### 2.11. Failure Handling

If at any step something deviates (missing info, failed assumption, test failure, etc.), then:

1. Output a **3-bullet summary** of the issue.
2. Suggest **2 alternative approaches**.
3. Propose the single best next action.
4. Pause with `<<AWAIT_CONFIRM: Choose alternative or revisit?>>`.

### 2.12. Additional Global Rules

- Use fixed schemas for Assumptions, Plans, Risks, Tests, Deliverables.
- Brevity rules: no more than **5 bullets** per section; word limits as above.
- Brief rationales only: ≤3 bullets each.
- Stop tokens: `<<AWAIT_CONFIRM: ...?>>`; the model should not continue past unless confirmation is given.
- No free-form chain-of-thought beyond rationale bullets.
- On completion of EXECUTE, record evidence in the active spec and the relevant
  commit, pull request, CI run, or issue.
- Do not create standalone implementation plans or dated update diaries under
  `docs/`; use an active spec when structured delivery is needed.

## 3. Examples

```
<<AWAIT_CONFIRM: Plan acceptable or revise?>>
```

## 4. Rationale / Justification

Structured planning is essential for managing the complexity of multi-file changes and feature work. This protocol ensures that the agent's approach is
transparent, aligned with user expectations, and allows for explicit approval at critical junctures, thereby mitigating risks and improving the quality of
deliverables.

## 5. Related Information

This planning protocol is cross-referenced with the general preferences guide
for coordinating and applying repository rules.

# References

- [General Preferences](./AGENT-GUIDE-General-Preferences.md)
- `docs/specs/README.md` (active specification lifecycle and authority boundaries)
- `docs/history/spec-closure-log.md` (closure evidence)
- `docs/history/spec-archive-index.md` (closed specification discovery)
