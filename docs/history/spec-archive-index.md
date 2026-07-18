---
title: Spec archive index
doc_type: history
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Spec Archive Index

This index makes removed, archived, superseded, and explicitly retained
lifecycle packages discoverable without treating them as active implementation
contracts.

## Entries

| Spec ID | Title | Package path | Status | Final spec commit | Cleanup commit | Closure action | Durable destinations | Verification |
|---------|-------|--------------|--------|-------------------|----------------|----------------|----------------------|--------------|
| 006-repository-review-skill | Repository Review Skill | removed; recover from Git | removed | `62dac67` | pending | removed | `.agents/skills/review-timelocker/`; `AGENTS.md` | `docs/history/spec-closure-log.md` |
| 005-project-charter | Project Charter | removed; recover from Git | removed | `ad96064` | `efafc2b` | removed | `CHARTER.md`; `README.md`; `docs/README.md`; `AGENTS.md`; `docs/specs/README.md`; `docs/specs/001-cli-consolidation-stabilization/requirements.md` | `docs/history/spec-closure-log.md` |
| 004-repository-hygiene | Repository Hygiene | removed; recover from Git | removed | `52e5a59` | `fc849cd` | removed | `AGENTS.md`; `README.md`; `CHANGELOG.md`; `docs/guides/ai-agent/`; `docs/resources/`; `docs/templates/`; `docs/specs/001-cli-consolidation-stabilization/` | `docs/history/spec-closure-log.md` |
| 003-migrate-legacy-kiro-specs | Migrate Legacy Kiro Specifications | removed; recover from Git | removed | `7fb10e5` | `8e28714` | removed | `docs/reference/timelocker-cli-command-hierarchy.md`; `docs/guides/user/recovery-operations-guide.md`; `docs/specs/001-cli-consolidation-stabilization/requirements.md`; `docs/history/` | `docs/history/spec-closure-log.md` |
| 002-prune-historical-documentation | Prune Historical Documentation | removed; recover from Git | removed | `0d10228` | `c25a11e` | removed | `docs/README.md`; `docs/DOCUMENTATION-STATUS.md`; `docs/guides/ai-agent/`; `docs/history/` | `docs/history/spec-closure-log.md` |
| 000-adopt-spec-lifecycle-manager | Adopt Spec Lifecycle Manager | removed; recover from Git | removed | `c84dc3a` | `3855e68` | removed | `docs/specs/README.md`; `docs/guides/ai-agent/`; `docs/history/` | `docs/history/spec-closure-log.md` |
| legacy-cli-consolidation-stabilization-plan | RFC: CLI Consolidation Stabilization Plan | removed; recover from Git | superseded | `ce23d07` | `3855e68` | removed | `docs/specs/001-cli-consolidation-stabilization/requirements.md`; `docs/history/spec-archive-index.md` | `docs/specs/001-cli-consolidation-stabilization/traceability.md` |

## Legacy Gaps

| Spec ID | Gap | Disposition |
|---------|-----|-------------|

## Maintenance

- Update this index and `spec-closure-log.md` together.
- Use a real commit hash for the final spec and closure cleanup commits.
- Active packages remain indexed only in `docs/specs/README.md`.
