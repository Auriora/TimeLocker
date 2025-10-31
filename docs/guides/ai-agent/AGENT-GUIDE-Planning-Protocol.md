---
type:        "agent_requested"
name:        "Planning protocol"
priority:    30
scope:       "planning-flow"
description: "Use structured planning for complex, multi-file changes or feature work."
cross_reference: ["preferences.md"]
apply_when:   "task_type == \"complex_change\""
---

# AI Agent Rule/Guide: Planning Protocol

- **Type**: agent_requested
- **Priority**: 30
- **Scope**: planning-flow
- **Description**: Use structured planning for complex, multi-file changes or feature work.
- **Cross-Reference**: preferences.md
- **Apply When**: task_type == "complex_change"

## 1. Purpose

This protocol defines a structured planning process for the AI agent when undertaking complex, multi-file changes or feature work. The purpose is to ensure a
clear, measurable, and risk-aware approach to task execution, requiring explicit user approval before proceeding to implementation.

## 2. Rule/Guideline Details

The agent must follow the phases below exactly, using “mode=PLAN” first and only entering “mode=EXECUTE” after user approval. The agent must use brief
rationales, fixed schemas, and verbosity limits. Steps must not be changed unless explicitly instructed by the user. If any instruction seems ambiguous, or
domain assumptions are detected, the agent must stop and ask for clarification.

### 2.1. Desired Outcome

- Define the desired state with measurable success criteria (both functional and non-functional).
- For each criterion: state how it can be **measured or tested**.
- Limit: max **5 bullets**, max **100 words**.

### 2.2. Scope & Assumptions

- Restate the problem; define all key terms.
- Enumerate explicit & implied assumptions.
- Ask clarifying questions if any success criterion, constraint, or dependency is missing.
- Limit: ≤ **5 bullets**, ≤ **100 words**.

### 2.3. Gap & Plan

- Identify gaps between Current State (if provided) and Desired Outcome.
- Propose a high-level plan (modules or steps) to bridge the gaps.
- Present in human-readable form: bullets or table. If a small reference block labeled "Structured reference" is included at the end, it must be clearly
  separated.
- Limit: ≤ 5 gaps, ≤ 5 plan steps, ≤ 150 words.

### 2.4. Risks

- List top risks in a table with columns: **Risk**, **If-then detector**, **Mitigation**.
- Limit to ≤ **5 risks**.
- Brief rationale: for each risk, 1-2 bullets explaining the likelihood & impact.

### 2.5. Tests

- Provide a test checklist for unit, integration, acceptance tests. Each item: description + pass/fail criterion.
- Limit: ≤ **7 items** total.
- If tests depend on risk or assumptions, explicitly link.

### 2.6. Deliverables

- Deliver the final plan and executive summary (mapping back to Desired Outcome).
- Restate any questions or assumptions in a structured reference block for confirmation.
- Limit: max **200 words** in summary.
- Reminder: upon completion, add/update a `docs/updates` entry (see `docs/updates/README.md`) when applicable.

### 2.7. Failure Handling

If at any step something deviates (missing info, failed assumption, test failure, etc.), then:

1. Output a **3-bullet summary** of the issue.
2. Suggest **2 alternative approaches**.
3. Propose the single best next action.
4. Pause with `<<AWAIT_CONFIRM: Choose alternative or revisit?>>`.

### 2.8. Additional Global Rules

- Use fixed schemas for Assumptions, Plans, Risks, Tests, Deliverables.
- Brevity rules: no more than **5 bullets** per section; word limits as above.
- Brief rationales only: ≤3 bullets each.
- Stop tokens: `<<AWAIT_CONFIRM: ...?>>`; the model should not continue past unless confirmation is given.
- No free-form chain-of-thought beyond rationale bullets.
- On completion of EXECUTE, add/update a `docs/updates` entry summarizing what was implemented and link it from `docs/updates/index.md`.

## 3. Examples

```
<<AWAIT_CONFIRM: Plan acceptable or revise?>>
```

## 4. Rationale / Justification

Structured planning is essential for managing the complexity of multi-file changes and feature work. This protocol ensures that the agent's approach is
transparent, aligned with user expectations, and allows for explicit approval at critical junctures, thereby mitigating risks and improving the quality of
deliverables.

## 5. Related Information

This planning protocol is cross-referenced with `preferences.md` for general project preferences and guidance on coordinating and applying other rules.

# References

- [General Preferences](./AGENT-GUIDE-General-Preferences.md)
- `docs/updates/README.md` (for updating implementation notes)
- `docs/updates/index.md` (for linking implementation notes)