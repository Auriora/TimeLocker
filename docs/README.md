---
title: TimeLocker documentation
doc_type: reference
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# TimeLocker Documentation

This tree documents accepted current behavior and active delivery work. Git
history—not a visible archive of old plans, reports, requirements, designs, or
status snapshots—preserves superseded context.

## Start Here

- [Project charter](../CHARTER.md)
- [Installation](./guides/user/installation.md)
- [Repository management](./guides/user/repository-management-guide.md)
- [S3-compatible services](./guides/user/s3-compatible-services.md)
- [Testing quick start](./4-testing/quickstart-testing.md)
- [CLI command hierarchy](./reference/timelocker-cli-command-hierarchy.md)
- [Repository orientation and change map](./reference/repo-orientation-and-change-map.md)
- [Active specifications](./specs/README.md)

## Current Product State

TimeLocker is a Beta CLI application that wraps Restic for repository,
snapshot, backup, restore, credential, policy, scheduling, monitoring, and
integration workflows. The CLI is the supported user interface. There is no
implemented REST API, database-backed application store, desktop GUI, or
mobile client.

The CLI consolidation and stabilization package is complete. Its accepted
service and ownership boundaries are documented in the
[Service Layer Integration Guide](./3-implementation/service-layer-integration.md)
and [Repository Orientation and Change Map](./reference/repo-orientation-and-change-map.md).
GitHub owns assignment and issue status; the [active-spec index](./specs/README.md)
lists any governed delivery work.

## Documentation Map

| Need | Current source |
|------|----------------|
| Product and command behavior | `guides/user/`, `reference/` |
| System structure and decisions | `2-architecture/` |
| Code structure and integration | `3-implementation/` |
| Testing commands and environments | `4-testing/` |
| Contributor guidance | `guides/developer/` |
| Agent rules | `guides/ai-agent/` |
| Release/version process | `processes/` |
| Durable document starters | `templates/` |
| Documentation resources | `resources/` |
| Active delivery contracts | `specs/` |
| Compact lifecycle evidence | `history/` |

`1-requirements/` currently contains the durable-document contract and template
only; do not treat removed Kiro requirements or historical specs as current
product requirements. When accepted product requirements need durable coverage,
add a current-state document there or promote them from an active spec.

## Authority Boundaries

- The project charter owns enduring mandate, boundaries, governance, and
  success measures.
- Code, tests, configuration, and generated contracts override stale prose.
- Durable docs describe implemented and accepted current behavior.
- Active specs describe approved intended changes until promotion and closure.
- GitHub issues own assignment and issue state.
- Git history preserves completed plans, implementation diaries, reviews, and
  superseded requirements/designs.
- `history/` contains only compact spec closure breadcrumbs; it is not a visible
  document archive.

## Documentation Rules

1. Keep one current source per concept and link to it rather than duplicating it.
2. Do not add permanent implementation diaries, completion reports, local issue
   snapshots, or standalone plans.
3. Put non-trivial active work under `specs/[###-slug]/`; promote lasting
   behavior before closure and then remove the package.
4. Put unapproved future work in GitHub or a new active spec, not current-state
   architecture or reference docs.
5. Record validation in the owning spec, commit, pull request, or CI result.
6. Run internal-link and Markdown checks after moving or deleting docs.

## Historical Recovery

Use `git log -- <path>` and `git show <commit>:<path>` to recover deleted
historical material. For closed spec identity and durable destinations, consult
[the closure log](./history/spec-closure-log.md) and
[archive index](./history/spec-archive-index.md).
