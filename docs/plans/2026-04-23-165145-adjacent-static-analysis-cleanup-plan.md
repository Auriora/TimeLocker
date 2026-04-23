---
title: "RFC: Adjacent Static Analysis Cleanup Plan"
id: "rfc-2026-04-23-165145-adjacent-static-analysis-cleanup-plan"
type: [ plan ]
status: [ draft ]
owner: "Codex"
last_reviewed: "23-04-2026"
tags: [plan, typing, static-analysis, scheduling, services]
links:
  tooling: [basedpyright, ruff, python-agent-ide]
---

# RFC: Adjacent Static Analysis Cleanup Plan

- **Owner**: Codex
- **Status**: Draft
- **Last Updated**: 23-04-2026
- **Created Date**: 23-04-2026
- **Audience**: Engineering Teams, Reviewers

## 1. Purpose

Capture the follow-up work needed after the `tool_manager.py` cleanup to address adjacent static-analysis debt in the connected services and scheduling modules. The goal is to remove substantive type-contract drift first, then close out local annotation debt, and finish with a targeted verification sweep over the touched slice.

## 2. Problem Statement

The adjacent sweep around `src/TimeLocker/services/tool_manager.py` found three follow-up areas:

- `src/TimeLocker/services/parallel_execution_optimizer.py` has substantive contract issues including an import cycle with `tool_manager.py`, `ToolOptionValue` values flowing into `int` parameters, and `Any` propagation from `psutil`.
- `src/TimeLocker/scheduling/schedule_manager.py` has heavy annotation debt, legacy typing syntax, and callback typing gaps around policy update registration.
- `src/TimeLocker/scheduling/platform_adapter.py` has lighter cleanup debt, mainly legacy typing and an unannotated logger.

Success criteria:

- Fresh targeted diagnostics for the three files report no blocker-level basedpyright issues.
- Service and scheduling helper signatures align with actual runtime contracts.
- A final adjacent verification pass produces only intentionally deferred debt, if any, and documents that remainder explicitly.

## 3. Proposed Solution

Work the cleanup in the following order:

1. `parallel_execution_optimizer.py`
   - Break or reduce the import-cycle pressure between optimizer and tool manager.
   - Narrow configuration-option reads to concrete `int` values before passing them into optimizer math and constructor paths.
   - Replace `Any`-shaped resource values with explicit numeric normalization at the `psutil` boundary.
   - Remove local implicit string-concatenation and partial-unknown list-building warnings while preserving behavior.
2. `schedule_manager.py`
   - Add explicit attribute annotations for the initialized collaborators and caches.
   - Convert legacy `Optional/List/Dict` usage to modern syntax where touched.
   - Type the policy update callback registration path against the actual client contract.
   - Review deprecated UTC timestamp creation and replace with timezone-aware equivalents where safe.
3. `platform_adapter.py`
   - Convert legacy `List[...]` annotations to modern `list[...]`.
   - Annotate the class logger attribute and re-run targeted diagnostics.
4. Verification
   - Re-run `diagnostics_for_files` on the cleaned set.
   - Run `post_edit_feedback` for the touched slice.
   - Document residual debt or follow-up work if the sweep uncovers additional adjacent files.

## 4. Alternatives

- Cleanup all scheduling and services files in one pass.
  This is higher risk and makes it harder to distinguish real contract fixes from broad annotation churn.
- Stop after `parallel_execution_optimizer.py`.
  This would leave the scheduling-side contract drift identified by the adjacent sweep unresolved.
- Defer all deprecated typing cleanup.
  This reduces immediate scope but leaves mixed syntax and unclear callback typing in the highest-noise scheduling modules.

## 5. Impact

- Affected systems or teams
  Scheduling services, backup-tool orchestration, and the static-analysis workflow used for MCP validation.
- Risks and mitigations
  Import-cycle changes can alter runtime import order.
  Mitigation: keep edits minimal, prefer narrowing types over structural moves unless a cycle cannot be resolved locally.
- Migration or rollout plan
  Apply file-by-file cleanup in the listed order and verify after each file rather than landing all changes blind.

## 6. Task Set

1. Clean `src/TimeLocker/services/parallel_execution_optimizer.py`
   Success check: targeted diagnostics show cycle/argument-type/`Any`-propagation issues resolved for this file.
2. Clean `src/TimeLocker/scheduling/schedule_manager.py`
   Success check: targeted diagnostics collapse the current annotation and callback typing warnings to zero or an explicitly accepted remainder.
3. Clean `src/TimeLocker/scheduling/platform_adapter.py`
   Success check: targeted diagnostics show no remaining local warnings.
4. Re-run adjacent static-analysis sweep
   Success check: `diagnostics_for_files` across the cleaned slice reports no fresh blocker-level findings.
5. Record implementation/update notes
   Success check: add a `docs/updates/` entry summarizing what was implemented and verified.

# References

- `src/TimeLocker/services/tool_manager.py`
- `src/TimeLocker/services/parallel_execution_optimizer.py`
- `src/TimeLocker/scheduling/schedule_manager.py`
- `src/TimeLocker/scheduling/platform_adapter.py`
- `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md`
