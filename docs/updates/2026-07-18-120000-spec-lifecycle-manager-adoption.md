---
title: "Update: Spec Lifecycle Manager adoption"
id: "update-2026-07-18-120000-spec-lifecycle-manager-adoption"
type: [ update ]
status: [ approved ]
owner: "Codex"
last_reviewed: "18-07-2026"
tags: [update, documentation, governance, spec-lifecycle]
links:
  tooling: [spec-lifecycle-manager, python-agent-ide]
---

# Update: Spec Lifecycle Manager Adoption

- **Owner**: Codex
- **Created Date**: 18-07-2026
- **Audience**: Contributors, maintainers, coding agents
- **Related**: `docs/specs/000-adopt-spec-lifecycle-manager/`
- **Scope**: Documentation and agent governance

## 1. Purpose

Convert TimeLocker from standalone active plans to evidence-bearing
specification packages while preserving durable documentation, GitHub issue
tracking, and historical implementation records.

## 2. Summary

- Added the active-spec lifecycle, package contract, authority boundaries, and
  closure history.
- Migrated the only active legacy plan into Spec 001.
- Preserved completed and superseded plans as history.
- Updated the repository entry point, planning protocol, documentation rules,
  documentation hub, and issue crosswalk.

## 3. Implementation Notes

- Spec 000 governs this adoption and remains active until validation evidence
  and a final spec commit allow closure.
- Spec 001 preserves completed CLI consolidation tasks T001-T004 and leaves
  repository resolution, service-manager reduction, monitoring consolidation,
  final validation, promotion, and closure readiness as T005-T010.
- No runtime code, dependency, plugin installation, backlog, or roadmap was
  added.
- Lifecycle, link, and formatting validation is recorded in Spec 000's
  `verification.md`.

## 4. Documentation & Links

- `docs/specs/README.md`
- `docs/specs/000-adopt-spec-lifecycle-manager/`
- `docs/specs/001-cli-consolidation-stabilization/`
- `docs/history/spec-closure-log.md`
- `docs/history/spec-archive-index.md`

## 5. Review Outcome

- **Review state**: Approved
- **Evidence reviewed**: Package scan/lint/readiness, task-state audit, archive-index validation, internal-link check, and `git diff --check`
- **Open follow-up**: Commit and close Spec 000 when requested; implement Spec 001 T005-T010 separately

# References

- `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md`
- `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md`
