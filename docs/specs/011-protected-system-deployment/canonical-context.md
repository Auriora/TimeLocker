---
title: Protected system deployment canonical context
doc_type: spec
artifact_type: canonical-context
status: draft
owner: Auriora Team
last_reviewed: 2026-07-28
---

# Canonical Context

## Purpose

This package turns a Spec 010 acceptance harness into a future supported
administrator workflow. This map prevents the proposed workflow, temporary
acceptance evidence, or removed spec history from being mistaken for current
installation behavior.

## Authority Hierarchy

The package is canonical only for its approved implementation slice while
active. It does not override user or platform instructions, `AGENTS.md`,
`CHARTER.md`, security policy, source and test contracts, generated artifacts,
or live system evidence.

## Always-Canonical External Sources

| Source | Authority reason | Handling |
|--------|------------------|----------|
| `AGENTS.md` and `docs/guides/ai-agent/` | Repository workflow and operational instructions | Read before authoring, implementation, validation, or deployment. |
| `CHARTER.md` | Project mandate, boundaries, governance, and approval rights | Stop if deployment work expands into a remote management service or unattended product update policy. |
| Current source, tests, package metadata, and live host evidence | Implementation and runtime truth | Reconcile conflicts; proposed prose does not override current behavior. |
| `docs/1-requirements/system-operations.md` | Accepted protected-operation and administrator boundary | Extend without weakening authorization, immutable release, or fail-closed requirements. |
| `docs/processes/version-management.md` | Accepted release preparation, publication, activation, and rollback separation | Preserve the publication/deployment boundary. |

## Spec-Canonical Working Sources

| Source | Role | Scope | Notes |
|--------|------|-------|-------|
| `requirements.md` | Proposed observable deployment behavior | Spec 011 | Requires review before design. |
| future `design.md` | Deployment architecture and decisions | Spec 011 | Must reconcile with the proven Spec 010 transaction. |
| future `tasks.md` | Dependency-aware execution index | Spec 011 | Implementation must not begin from tasks alone. |

## Imported Sources

| Spec path | Source path | Source revision or date | Status | Canonical scope | Promotion target |
|-----------|-------------|-------------------------|--------|-----------------|------------------|
| requirements | `docs/guides/user/installation.md` | reviewed 2026-07-27 | supersedes | Statement that no supported protected installer exists | same path |
| requirements | `docs/processes/version-management.md` | current checkout | adapted | Protected activation and rollback invariants | same path |
| requirements | `docs/1-requirements/system-operations.md` | reviewed 2026-07-26 | adapted | Root-only maintenance and immutable release requirements | same path |
| requirements | `scripts/deploy_t011_linux.py` | commit `a67c83ac09ac29b94a3ed481ee536b3380db3337` | background | Proven acceptance transaction and failure lessons | future supported deployment implementation |
| requirements | Spec 010 T011 live evidence | 2026-07-27 to 2026-07-28 | summarized | Successful Linux Mint activation and retained rollback state | verification and operator runbook |

## Non-Canonical Background Sources

| Source | Reason non-canonical | Handling |
|--------|----------------------|----------|
| Removed Specs 007-009 recovered from Git | Closed delivery scaffolding | Use only for historical rationale; durable promoted documents own current behavior. |
| `/tmp/timelocker-*` scripts and artifacts from acceptance work | Ephemeral, unversioned, or build-local evidence | Do not use as a supported deployment interface or durable procedure. |
| `scripts/deploy_t011_linux.py` after Spec 010 closure | Acceptance-specific name and contract | Preserve as evidence or compatibility input until Spec 011 replaces or retires it explicitly. |

## Promotion Map

| Spec-local content | Durable destination or route | Required before closure |
|--------------------|------------------------------|-------------------------|
| Supported install, upgrade, status, and rollback behavior | `docs/1-requirements/system-operations.md` | yes |
| Deployment components, trust boundaries, and platform adapters | `docs/2-architecture/system-architecture.md` | yes |
| Administrator procedure and troubleshooting | `docs/guides/user/installation.md` and a durable deployment runbook | yes |
| Release artifact and host activation relationship | `docs/processes/version-management.md` | yes |
| Administrator command reference | `docs/reference/timelocker-cli-command-hierarchy.md` or a dedicated reference | yes |
| Live Windows implementation | follow-up spec or issue if not accepted in this package | yes |

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Overview: [README.md](./README.md)
