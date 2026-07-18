---
title: "Active Specification Packages"
doc_type: reference
status: active
owner: "Auriora Team"
last_reviewed: 2026-07-18
---

# Active Specification Packages

This directory contains temporary delivery contracts for work that needs more
coordination than a direct, low-risk change. Durable documentation describes the
accepted current state; active specs describe an intended change until its
accepted content has been promoted and the package is closed.

## Current Packages

- [`000-adopt-spec-lifecycle-manager/`](./000-adopt-spec-lifecycle-manager/) —
  conversion of TimeLocker's planning and documentation workflow.
- [`001-cli-consolidation-stabilization/`](./001-cli-consolidation-stabilization/) —
  remaining CLI consolidation work migrated from the legacy active plan.

## When a Spec Is Needed

Create a spec for multi-file features, migrations, architectural changes,
cross-cutting refactors, governance changes, or work whose acceptance and
validation would otherwise be ambiguous. Small fixes and narrow documentation
corrections may proceed directly when their scope and validation are clear.

## Lifecycle

1. **Intake and triage** — inspect durable docs, active specs, issue context,
   and repository rules; decide whether the work needs a spec.
2. **Specify** — create `requirements.md`, `design.md`, and `tasks.md`; add
   change-impact, verification, traceability, or open-decision artifacts when
   they reduce ambiguity.
3. **Approve** — obtain explicit user approval before implementation for work
   governed by the planning protocol.
4. **Implement and reconcile** — execute tasks in dependency order, record
   evidence, and reconcile drift whenever work resumes.
5. **Verify and promote** — run the package's validation plan and move accepted
   behavior into durable documentation.
6. **Close** — commit the final spec state, record closure in
   [`../history/spec-closure-log.md`](../history/spec-closure-log.md), update
   [`../history/spec-archive-index.md`](../history/spec-archive-index.md), and
   remove or archive the package according to the recorded decision.

## Package Contract

- `requirements.md` defines goals, non-goals, user stories, acceptance
  criteria, correctness properties, and durable sources.
- `design.md` maps requirements to the proposed implementation and validation.
- `tasks.md` is the evidence-bearing execution index, not a standalone plan.
- `change-impact.md` records changes and promotion targets when existing
  behavior or governance is affected.
- `verification.md` records commands, evidence, residual risks, and closure
  readiness.
- `traceability.md` maps requirements, design, tasks, verification, and durable
  destinations for larger packages.

Tasks use `[ ]` pending, `[~]` in progress, `[/]` partial, `[>]` routed,
`[-]` deferred/no-op, `[?]` decision needed, `[!]` attention needed, and `[x]`
complete and verified. A completed task must include evidence.

## Authority Boundaries

- GitHub issues remain authoritative for assignment and issue state.
- Active specs are authoritative for implementation scope, sequencing,
  acceptance criteria, and evidence.
- `docs/updates/` remains the chronological implementation diary.
- `docs/plans/` is retained for historical plans and must not receive new
  implementation plans.
- Durable requirements, architecture, implementation, testing, process, and
  reference documents remain authoritative after a spec closes.

Use the Spec Lifecycle Manager MCP tools for package discovery, readiness,
task context, validation planning, promotion, and closure checks. Do not copy
the plugin's scripts or fallback templates into this repository.
