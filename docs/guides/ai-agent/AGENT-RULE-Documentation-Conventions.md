---
type: "agent_requested"
name: "Documentation conventions"
priority: 20
scope: "docs/**"
description: "Keep documentation current-state oriented and use Git for history."
cross_reference: ["AGENT-GUIDE-General-Preferences.md", "AGENT-GUIDE-Planning-Protocol.md"]
apply_when: "task_changes_documentation == true"
---

# AI Agent Rule: Documentation Conventions

## Purpose

Keep `docs/` small, current, and authoritative. Git history preserves completed
delivery artifacts; the visible tree must not become an archive of plans,
requirements/design drafts, implementation diaries, reports, or issue snapshots.

## Current Structure

```text
docs/
├── README.md
├── 1-requirements/       # accepted durable product requirements
├── 2-architecture/       # implemented system structure and ADRs
├── 3-implementation/     # current code/integration guidance
├── 4-testing/            # current test commands and environment guidance
├── guides/               # user, developer, and agent guidance
├── processes/            # durable operational/release processes
├── proposals/            # short-lived proposals awaiting routing
├── reference/            # stable command, API, and configuration facts
├── specs/                # temporary active delivery packages
└── history/              # compact spec closure breadcrumbs only
```

Do not recreate `updates/`, `plans/`, `reports/`, `archive/`, `issues/`,
`traceability/`, or local project-task directories as permanent documentation
collections.

## Placement Rules

- Accepted requirements and invariants → `1-requirements/`.
- Implemented architecture and durable decisions → `2-architecture/`.
- Current code structure and integration guidance → `3-implementation/`.
- Current testing procedures → `4-testing/`.
- User/developer/agent procedures → `guides/`.
- Operational and release processes → `processes/`.
- Stable factual mappings and contracts → `reference/`.
- Non-trivial active implementation work → `specs/[###-slug]/`.
- Spec closure identity and commit evidence → `history/`.
- Assignment, issue state, backlog, and unapproved future work → GitHub.

## Lifecycle Rules

1. Durable docs describe accepted current state by default.
2. Active specs describe approved intended changes and are temporary.
3. Promote lasting requirements, design, contracts, operations, and validation
   guidance before closing a spec.
4. Commit a spec's complete final state, record compact closure evidence, and
   remove the package. Do not retain completed specs as visible history.
5. Store implementation evidence in the active spec, commit, pull request, CI,
   or issue. Do not create a permanent update diary.
6. Use `git log -- <path>` and `git show <commit>:<path>` for historical recovery.

## Content Rules

- One home per concept; reference instead of copying.
- Current docs must not link to legacy `.kiro/specs/`, deleted plans, dated
  updates, completion reports, or local issue/task snapshots.
- Do not mix proposed REST API, GUI, database, roadmap, or other future behavior
  into current architecture/reference docs. Route it to GitHub or an active spec.
- Replace orphaned requirement IDs with a current durable requirement, active
  spec acceptance criterion, code-derived contract, or no reference.
- Label experimental or deprecated behavior explicitly when it still exists.
- Prefer relative links and validate them after moves or deletions.

## Required Evidence

For documentation changes, record:

- documents changed or removed;
- current source used to validate claims;
- internal-link and Markdown results;
- lifecycle checks when specs are involved;
- residual uncertainty where behavior was not executed.

Evidence belongs in the active spec, commit message/body, pull request, CI, or
issue—not a new permanent documentation log.

## Review Checklist

- [ ] Content describes implemented current state or is explicitly active-spec intent.
- [ ] No concept is duplicated across durable documents.
- [ ] No historical plan/report/update/local issue artifact was added.
- [ ] No legacy `.kiro/specs/` or deleted-document reference remains.
- [ ] Future-only behavior is routed out of current-state docs.
- [ ] Active-spec promotion and closure state is accurate.
- [ ] Links and Markdown structure were checked.

# References

- [Documentation hub](../../README.md)
- [Planning protocol](./AGENT-GUIDE-Planning-Protocol.md)
- [Active specifications](../../specs/README.md)
- [Spec closure log](../../history/spec-closure-log.md)
