---
title: Spec archive index
doc_type: history
status: active
owner: Auriora Team
last_reviewed: 2026-07-26
---

# Spec Archive Index

This index makes removed, archived, superseded, and explicitly retained
lifecycle packages discoverable without treating them as active implementation
contracts.

## Entries

| Spec ID | Title | Package path | Status | Final spec commit | Cleanup commit | Closure action | Durable destinations | Verification |
|---------|-------|--------------|--------|-------------------|----------------|----------------|----------------------|--------------|
| 009-system-cli-tray-retention | System CLI, independent tray, retention, and control | removed; recover from Git | removed | `d4ce71dd05cb5d7278bf36a9fc43e557d68e1e31` | pending-cleanup-commit | removed | `docs/1-requirements/system-operations.md`; `docs/2-architecture/system-architecture.md`; `docs/2-architecture/scheduling-system.md`; `docs/3-implementation/service-layer-integration.md`; `docs/guides/user/installation.md`; `docs/guides/developer/scheduling-guide.md`; `docs/SYSTEM-TRAY-SETUP.md`; `docs/reference/timelocker-cli-command-hierarchy.md`; `docs/guides/user/backup-operations-troubleshooting.md`; `docs/processes/version-management.md`; `docs/README.md`; `docs/DOCUMENTATION-STATUS.md`; `docs/specs/README.md` | `docs/history/spec-closure-log.md` |
| 007-release-readiness-stabilization | Release readiness stabilization requirements | removed; recover from Git | removed | `7fd11f9aa1cbc670d5e8b429aede4a7c01e185a4` | `6334af0690b5b9e8b6575042269e5b73914a9295` | removed | `README.md`; `CHANGELOG.md`; `.github/workflows/test-suite.yml`; `.github/workflows/artifact-smoke.yml`; `.github/workflows/release-validation.yml`; `.github/workflows/release.yml`; `docs/4-testing/README.md`; `docs/guides/user/installation.md`; `docs/guides/user/recovery-operations-guide.md`; `docs/guides/developer/scheduling-guide.md`; `docs/processes/version-management.md`; `docs/processes/README.md` | `docs/history/spec-closure-log.md` |
| 008-npbackup-migration-parity | NPBackup migration parity requirements | removed; recover from Git | removed | `5830194` | `1bfea08` | removed | `docs/guides/user/recovery-operations-guide.md`; `docs/guides/developer/scheduling-guide.md` | `docs/history/spec-closure-log.md` |
| 001-cli-consolidation-stabilization | CLI Consolidation Stabilization | removed; recover from Git | removed | `a1bb654` | `b8df9e9` | removed | `docs/3-implementation/service-layer-integration.md`; `docs/reference/repo-orientation-and-change-map.md`; `docs/specs/README.md`; `docs/history/` | `docs/history/spec-closure-log.md` |
| 002-repository-safety-release-readiness | Repository Safety and Release Readiness | removed; recover from Git | removed | `4aff166` | `c6ed9ee` | removed | `README.md`; `docs/2-architecture/`; `docs/guides/user/installation.md`; `docs/guides/user/per-repo-credentials.md`; `docs/processes/version-management.md`; `docs/DOCUMENTATION-STATUS.md`; `docs/specs/README.md` | `docs/history/spec-closure-log.md` |
| 006-repository-review-skill | Repository Review Skill | removed; recover from Git | removed | `62dac67` | `82f0247` | removed | `.agents/skills/review-timelocker/`; `AGENTS.md` | `docs/history/spec-closure-log.md` |
| 005-project-charter | Project Charter | removed; recover from Git | removed | `ad96064` | `efafc2b` | removed | `CHARTER.md`; `README.md`; `docs/README.md`; `AGENTS.md`; `docs/specs/README.md`; `docs/history/` | `docs/history/spec-closure-log.md` |
| 004-repository-hygiene | Repository Hygiene | removed; recover from Git | removed | `52e5a59` | `fc849cd` | removed | `AGENTS.md`; `README.md`; `CHANGELOG.md`; `docs/guides/ai-agent/`; `docs/resources/`; `docs/templates/`; `docs/history/` | `docs/history/spec-closure-log.md` |
| 003-migrate-legacy-kiro-specs | Migrate Legacy Kiro Specifications | removed; recover from Git | removed | `7fb10e5` | `8e28714` | removed | `docs/reference/timelocker-cli-command-hierarchy.md`; `docs/guides/user/recovery-operations-guide.md`; `docs/3-implementation/service-layer-integration.md`; `docs/history/` | `docs/history/spec-closure-log.md` |
| 002-prune-historical-documentation | Prune Historical Documentation | removed; recover from Git | removed | `0d10228` | `c25a11e` | removed | `docs/README.md`; `docs/DOCUMENTATION-STATUS.md`; `docs/guides/ai-agent/`; `docs/history/` | `docs/history/spec-closure-log.md` |
| 000-adopt-spec-lifecycle-manager | Adopt Spec Lifecycle Manager | removed; recover from Git | removed | `c84dc3a` | `3855e68` | removed | `docs/specs/README.md`; `docs/guides/ai-agent/`; `docs/history/` | `docs/history/spec-closure-log.md` |
| legacy-cli-consolidation-stabilization-plan | RFC: CLI Consolidation Stabilization Plan | removed; recover from Git | superseded | `ce23d07` | `3855e68` | removed | `docs/3-implementation/service-layer-integration.md`; `docs/history/spec-archive-index.md` | `docs/history/spec-closure-log.md` |

## Legacy Gaps

| Spec ID | Gap | Disposition |
|---------|-----|-------------|

## Maintenance

- Update this index and `spec-closure-log.md` together.
- Use a real commit hash for the final spec and closure cleanup commits.
- Active packages remain indexed only in `docs/specs/README.md`.
