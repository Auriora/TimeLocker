---
title: Project charter design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Technical Design

## Overview

Add one durable charter and route the minimum repository entry points to it.
The charter is governance above delivery specs, not another product overview or
implementation plan.

## High-Level Design

Create one root-level `CHARTER.md` as durable governance above delivery specs.
Repository entry points link to it for purpose, boundaries, and decision rules;
they retain their existing operational or delivery responsibilities.

```text
CHARTER.md (enduring project governance)
├── README.md (user and contributor orientation)
├── docs/README.md (documentation orientation)
├── AGENTS.md (agent routing)
└── Spec 001 (bounded CLI delivery contract)
```

Spec 005 may coexist with Spec 001 because it is documentation-only, does not
change CLI runtime or Spec 001 tasks, and closes immediately after promotion.

## Components

### Charter

Use short narrative sections and lists for:

- mandate and problem statement;
- intended users and value;
- operating principles;
- in-scope responsibilities and explicit exclusions;
- governance roles and decision rights;
- project success measures;
- relationship to issues, specs, durable docs, code, and tests;
- change rules and the practical next path.

The charter uses current-state labels and avoids dense governance tables.

### Authority Links

- `README.md`: add Project Direction near the initial orientation.
- `docs/README.md`: put the charter first in Start Here and describe its
  authority boundary.
- `AGENTS.md`: add the charter to general project context without copying its
  rules.
- Spec 001 requirements: add the charter to the durable baseline and state that
  it constrains delivery without changing the package scope.

## Low-Level Design

Create `CHARTER.md` with repository frontmatter and stable section headings.
Use relative Markdown links from each entry point. Add only a short authority
sentence or list item to supporting documents; do not copy charter principles,
boundaries, governance rules, or success measures into them. In Spec 001, add a
durable-baseline bullet without changing requirement IDs, acceptance criteria,
task state, or sequencing.

## Data And Contract Impact

No data, API, CLI, configuration, schema, or runtime contract changes. The only
new contract is repository governance expressed in durable prose.

## Error Handling

- If a charter statement conflicts with code-derived current behavior, correct
  the charter before promotion.
- If ownership requires a named individual, retain role-based ownership and
  route the naming decision to the user.
- If Spec 001 loses readiness, reconcile only the charter-related baseline link
  and do not alter its implementation requirements.

## Operational Considerations

- Rollback is a Git revert of documentation commits.
- No release note, deployment, migration, or security review is required.
- A documentation-architect review checks authority, duplication, readability,
  and reader paths before closure.

## Validation Strategy

- Run the repository link checker and Git whitespace check.
- Run Agent Workbench Markdown checks on the charter and changed front doors.
- Run Spec 005 lint, readiness, task audit, evidence, promotion, and closure
  checks.
- Run Spec 001 lint and readiness after the baseline link is updated.
- Scan for duplicated mandate/governance text outside the charter.

## Open Questions

None. The approved ownership assumption is Auriora Team with role-based project
stewardship.

## Related Artifacts

- Requirements: `requirements.md`
- Tasks: `tasks.md`
- Change Impact: `change-impact.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
