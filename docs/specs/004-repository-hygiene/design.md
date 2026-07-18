---
title: Repository hygiene design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Technical Design

## Overview

Apply a documentation-first normalization: remove duplicated rule sources,
repair current entry points, move documentation assets to one canonical path,
replace scattered templates with a small central set, and delete working-history
material whose durable outcome already exists in code or policy.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| Requirement 1 | AC1-AC3 | Instruction authority and rule normalization | Content search and Markdown checks |
| Requirement 2 | AC1-AC3 | Front-door rewrite and canonical resources | Link checker, path checks, focused script validation |
| Requirement 3 | AC1-AC3 | History removal and central templates | Git inventory, focused tests, link checks |
| Requirement 4 | AC1-AC2 | Cross-spec sequencing and lifecycle closure | Lifecycle readiness, audit, and closure checks |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | Remove active legacy paths and scan tracked text | `rg` plus link checker | Historical closure-log wording is allowed when clearly historical. |
| CP-002 | Move assets and update all consumers atomically | Existence and consumer-path checks | Root `resources/` remains product branding. |
| CP-003 | Gate Spec 001 T005 on closed Spec 004 | Lifecycle readiness and task audit | No Spec 001 implementation occurs in this package. |

## High-Level Design

### Instruction Authority

`AGENTS.md` remains a short router. Detailed rules live only under
`docs/guides/ai-agent/`. Remove `.kiro/steering/` entirely while preserving its
MCP settings sibling. Rewrite copied rules around this Python/Typer project and
its actual test/tool configuration.

### Front Door And Resources

Rewrite stale README structure and links from the actual tracked tree. Align
the coverage badge with `pyproject.toml`. Move `docs/.resources/` to
`docs/resources/`; update README and JSON conversion consumers in the same
slice. Product branding stays in root `resources/`.

### Durable Documentation Shape

Use `docs/templates/` for a minimal generic document template, decision record,
and agent-instruction template with an index explaining intended use. Remove
scattered `_template` files after updating any current references. Do not add a
repository spec-package template because the installed lifecycle fallback is
the authority.

Delete the pickle investigation only after current serialization behavior is
validated. Remove empty legacy directories after tracked files are gone.

## Files And Boundaries

- Instruction files: `AGENTS.md`, `.kiro/steering/`,
  `docs/guides/ai-agent/`.
- Front door: `README.md`, `CHANGELOG.md`, relevant documentation indexes.
- Resources and consumers: `docs/.resources/`, `docs/resources/`,
  `scripts/json2command_definition/`, and any discovered references.
- Templates: current scattered `docs/**/_template*` files and
  `docs/templates/`.
- Historical material: `docs/troubleshooting/pickle-error-investigation.md`
  and empty legacy directories.
- Lifecycle: Specs 001 and 004 plus compact history indexes at closure.
- Out of scope: `src/TimeLocker/` behavior changes and Spec 001 T005-T010.

## Low-Level Design

Apply path changes as exact tracked-file replacements. Use repository-relative
Markdown links, preserve existing YAML frontmatter where a document has it, and
update every discovered consumer in the same task as a move or deletion. Rule
rewrites retain only commands and frameworks confirmed by `pyproject.toml`, the
current tree, and repository scripts. No runtime interface changes are added.

## Error Handling

If a path has an undiscovered consumer, retain compatibility until the
consumer is updated. If pickle validation fails, rewrite the investigation as a
current runbook and leave the removal task incomplete. If lifecycle checks find
unpromoted content, keep Spec 004 active until durable promotion is complete.

## Security, Trust, And Access

No network, credential, or production access is required. Preserve
`.kiro/settings/mcp.json`; do not expose environment values in documentation.

## Migration And Compatibility

Documentation paths change atomically in one repository commit. Git retains the
removed working-history content. Spec 004 is a temporary governance prerequisite
and must close before Spec 001 product implementation resumes.

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Lifecycle lint/readiness/audit/closure | Requirement 4, CP-003 | `verification.md` | none expected |
| Markdown and internal-link checks | Requirements 1-3 | `verification.md` | External links are not exercised |
| Tracked-path and stale-term scans | CP-001, CP-002 | `verification.md` | Clearly historical log entries require review |
| Focused resource/pickle checks | Requirement 2 AC3, Requirement 3 AC1 | `verification.md` | Test availability may limit pickle coverage |
| Full test suite | Regression boundary | `verification.md` | Existing unrelated failures will be recorded |

## Downstream Task Guidance

- Complete tasks in dependency order; do not start Spec 001 implementation.
- Update task evidence after each coherent slice.
- Reconcile both active packages after any sequencing change.
- Promote accepted policy to durable docs before closing Spec 004.

## Operational Considerations

This change affects repository navigation and agent behavior only. Rollback is
the normal Git revert path.

## Open Questions

- None. The user approved removal of duplicated steering files, canonical
  `docs/resources/`, central templates, obsolete investigation removal after
  validation, and temporary Spec 004 sequencing.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
