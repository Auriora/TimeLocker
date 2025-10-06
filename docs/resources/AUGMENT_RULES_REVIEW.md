# Augment AI Rules Review

Date: 2025-10-06
Reviewer: Junie (AI)
Scope: Review of all rules in .augment/rules for clarity, completeness, potential unintended consequences, and recommended improvements.

---

## Executive Summary

- planning.md is overly prescriptive and marked as always_apply, which risks blocking normal development workflow and automation in this repo.
- testing.md and documentation.md are too minimal to be useful; they miss critical project-specific practices.
- git.md is generally sound but could benefit from more detail and alignment with existing CONTRIBUTING.md to avoid conflicts.
- Recommend right‑sizing enforcement levels (type field), clarifying scope, and enriching content with concrete, repo‑specific guidance and exceptions.

---

## General Observations

- Front matter type usage is inconsistent:
    - planning.md: type: "always_apply" (very strong; applies to all interactions).
    - testing.md, documentation.md, git.md: type: "agent_requested" with placeholder descriptions.
- Potential consequences:
    - An always_apply planning gate with stop tokens can deadlock automation (e.g., CI bots, scripted agents) or conflict with this repo’s established
      workflow (update_status/submit tools).
    - Sparse rules provide little value and may lead to divergent interpretations.
- Recommendation:
    - Use types to reflect intent: prefer scoped activation (e.g., only for planning tasks/tests/doc changes) rather than global always_apply.
    - Replace placeholder descriptions with concise, actionable descriptions.

---

## File-by-File Review

### 1) .augment/rules/planning.md

Strengths:

- Encourages clarity, explicit assumptions, risks, and tests before execution.
- Provides structured templates that can improve consistency.

Concerns and unintended consequences:

- always_apply can force all interactions (even trivial fixes) into a gated Plan/Execute ceremony, increasing friction and cycle time.
- Stop tokens (<<AWAIT_CONFIRM: ...?>>) and hard word limits can conflict with tools/agents that don’t support interactive confirmations or need more context (
  e.g., design docs).
- "Do not change steps unless I explicitly instruct" reduces adaptability to repo‑specific processes (e.g., TimeLocker’s required update_status/submit tooling
  and test steps).
- Bans on “free‑form chain‑of‑thought” may be fine for privacy, but combined with strict brevity can reduce necessary rationale in complex changes.

Recommendations:

- Change type from always_apply to one of:
    - task_requested (or agent_requested) with description: "Use this planning flow for non‑trivial or multi‑file changes, refactors, or feature work."
    - Or keep always_apply but add explicit exceptions for: trivial edits, documentation typo fixes, CI config tweaks, and test label changes.
- Replace hard stop tokens with a non‑blocking confirmation pattern compatible with this repo’s workflow:
    - "Use update_status to publish a plan; proceed to execution only after reviewer (human) approval or explicit self‑approval in low‑risk cases."
- Relax word limits to guidance (soft limits), not hard rules, or make them CI‑enforceable only outside emergencies.
- Add explicit compatibility with repo tools: "Publish plans using update_status; finalize via submit."
- Clarify failure handling to align with issue triage in this repo (concise bullets, then next action, but no blocking token).

Suggested front matter:

```
---
type: "agent_requested"
description: "Structured planning for non‑trivial changes; publish via update_status; proceed on approval."
---
```

### 2) .augment/rules/testing.md

Strengths:

- Encourages standard test naming and placement.

Gaps/risks:

- Too minimal; lacks project‑specific pytest practices used here (fixtures, mocks, isolation, coverage).
- No guidance on external tool dependencies (restic), network isolation, or use of tmp_path.

Recommendations (augment content):

- Naming/placement:
    - Place tests under tests/ mirroring src/ structure; use test_*.py naming.
- Pytest practices:
    - Use pytest with type hints; prefer unittest.mock.patch context managers over manual monkey‑patching.
    - Use tmp_path/tmp_path_factory for filesystem isolation; no writes outside temp dirs.
    - Mark tests requiring external tools (e.g., restic) with a marker and skip if missing; default to offline, deterministic tests.
    - Avoid real network calls; mock boto3/b2sdk interactions.
    - Keep tests idempotent and order‑independent; no reliance on global state.
- Coverage:
    - Target tests to run with pytest -v and pytest --cov=src; aim for meaningful coverage, not just percentage.
- CI clarity:
    - Fail fast on flakey patterns; prefer deterministic time via freezegun or datetime injection.

Potential type change:

```
---
type: "always_apply"
description: "Baseline pytest conventions for this repo."
---
```

### 3) .augment/rules/git.md

Strengths:

- Aligns with Conventional Commits style; provides a clear template and types.

Gaps/risks:

- Might conflict with CONTRIBUTING.md if formats differ; lacks line‑length guidance and branch naming.
- "commits should always be done in logical groups" is good but subjective; no advice on squashing/rebase policy.

Recommendations:

- Add subject limits and formatting:
    - Subject in imperative mood, ≤ 72 chars; wrap body at ~72 chars.
- Cross‑reference CONTRIBUTING.md to avoid drift.
- Include branch naming guidance (e.g., feature/<short-desc>, fix/<issue-#>).
- Encourage linking issues with refs (e.g., "Refs #123", "Fixes #123").
- Clarify squashing policy: prefer squash merge for PRs unless history needs preservation.
- Optional: add Signed‑off‑by if this project requires DCO.

Suggested front matter:

```
---
type: "always_apply"
description: "Conventional commit style and git hygiene for this repo."
---
```

### 4) .augment/rules/documentation.md

Strengths:

- Encourages docs/ placement and Markdown usage.

Gaps/risks:

- "Preferably update documentation rather than creating new ones" may discourage needed new docs (e.g., new features, ADRs, SRS updates).
- Lacks docstring standards, linkage to SRS and PlantUML usage mentioned in guidelines.

Recommendations:

- Scope and content:
    - Place prose docs in docs/; keep README current; maintain SRS under docs/SDLC/SRS/.
    - Use reStructuredText or Markdown consistently; here, prefer Markdown with PlantUML diagrams where applicable.
    - Provide docstrings for all public APIs (PEP 257 style) with type hints.
    - Update docs when changing public APIs or behavior; include examples where useful.
    - Create new documents when introducing new features, ADRs, or significant changes; don’t overload a single file.
- Diagrams:
    - Use PlantUML for UML; check in .puml sources and exported artifacts if needed.
- Cross‑refs:
    - Link to Best Practices and Testing sections; ensure consistency with README/CONTRIBUTING.

Suggested front matter:

```
---
type: "always_apply"
description: "Documentation standards for code and prose in this repo."
---
```

---

## Alignment with Repo Workflow

- Ensure rules reference the project’s workflow tools:
    - Use update_status to publish plans/checkpoints and submit for finalization.
    - Tests should be runnable with pytest, including markers and coverage configuration from pytest.ini.
- Avoid hard interactive stop tokens that can’t be honored by CI/automation.

---

## Minimal Change Options

- Option A (non‑disruptive): Keep current rules as-is and adopt this review as guidance for future edits. No immediate enforcement change.
- Option B (targeted tweaks):
    - Downgrade planning.md to agent_requested with clear description.
    - Upgrade testing.md and documentation.md to always_apply with enriched content.
    - Keep git.md but add subject/line‑wrap guidance and references.
- Option C (comprehensive): Update all four files per recommendations and add a short README in .augment/ to explain rule types and activation.

---

## Next Steps

- Confirm desired enforcement level for planning (strict gate vs. advisory).
- If approved, I can submit minimal PR to adjust front matter types and expand testing/documentation rules with the concrete bullets above.
