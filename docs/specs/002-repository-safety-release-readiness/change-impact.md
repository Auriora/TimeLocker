---
title: Repository safety and release readiness change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Change Impact

## Durable Source Mapping

| Source | Authority for this change | Delta |
|--------|---------------------------|-------|
| `CHARTER.md` | Safety, security, supported-path, and current-doc boundaries | Implement without changing charter scope. |
| `README.md` and user guides | Installation and credential usage | Correct inaccurate or insecure guidance. |
| `docs/2-architecture/` | Current architecture | Remove unimplemented legacy designs. |
| Python package and tests | Executable behavior | Make restore, credential, and import behavior satisfy the requirements. |

## Proposed Changes

## Accepted Finding Deltas

| Finding | Current defect | Required delta | Promotion target |
|---------|----------------|----------------|------------------|
| TLR-001 | False overwrite policy stops at orchestration; Restic defaults to overwrite. | Carry and emit explicit `never` or `always`. | Architecture/data-flow and tests where lasting. |
| TLR-002 | Credential keys are derivable from host attributes. | Require explicit operator secret; document rotation. | Credential user guide. |
| TLR-003 | Installation points to unavailable PyPI package; release job is unrelated JavaScript. | Source install plus Python-native GitHub release workflow. | README, installation and release guidance. |
| TLR-004 | Tests create a second `src.TimeLocker` module identity. | Normalize Python tests and guard the boundary. | Test policy/guard. |
| TLR-005 | Durable architecture presents legacy future designs as current. | Rewrite to implemented CLI/service/Restic state. | `docs/2-architecture/`. |

## Sequencing Impact

Spec 001 is paused at T005 until Spec 002 implementation and validation are
complete. The namespace normalization touches tests used by Spec 001 but does
not change its CLI consolidation scope or acceptance criteria.

## Compatibility And Removal

- Restore interface gains an optional keyword with a safe default.
- Insecure host-derived credential unlock is removed without fallback.
- PyPI installation claims and JavaScript release assumptions are removed.
- Future-only architecture content is removed from the current documentation
  path rather than archived as requirements or design.

## Durable Promotion Checklist

- [x] Credential secret sources and legacy-store response are current in the user guide.
- [x] README and installation guidance identify source installation.
- [x] Release process matches the Python workflow.
- [x] Architecture documents match implemented components and flows.
- [x] Documentation status/indexes remain accurate.

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Supported installation and release behavior | `README.md`, `docs/guides/user/installation.md`, `docs/processes/version-management.md` | complete | Source install and Python release workflow documented. |
| Non-interactive credential secret contract | `docs/guides/user/per-repo-credentials.md` | complete | Explicit environment/file sources and rotation response documented. |
| Implemented component boundaries and flows | `docs/2-architecture/system-architecture.md`, `component-breakdown.md`, `data-flow.md` | complete | Current CLI/service/Restic architecture promoted. |
| Package identity invariant | `tests/TimeLocker/test_package_identity.py` | complete | Automated regression guard is the durable executable contract. |
