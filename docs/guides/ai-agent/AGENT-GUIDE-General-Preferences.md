---
type:        "always_apply"
name:        "General preferences"
priority:    50
scope:       ".*"
description: "General project preferences and guidance for coordinating and applying other rules"
cross_reference: ["documentation.md","git.md","planning.md","testing.md"]
apply_when:   "always"
---

# AI Agent Rule/Guide: General Preferences

- **Type**: always_apply
- **Priority**: 50
- **Scope**: .*
- **Description**: General project preferences and guidance for coordinating and applying other rules.
- **Cross-Reference**: documentation.md, git.md, planning.md, testing.md
- **Apply When**: always

## 1. Purpose

This document outlines the general project preferences and provides explicit guidance for the AI agent (Augment) on discovering, prioritizing, and consistently
applying other rule files. It ensures that all agent actions align with core project principles and maintain high code quality and transparency.

## 2. Rule/Guideline Details

### 2.1. Core Principles

- Code must follow SOLID and DRY principles.
- Code reviews must be thorough with refactoring suggestions to improve code quality.
- Prefer direct implementation to extensive planning and analysis phases where appropriate.
- Always double-check during testing or implementation if any changes have been lost or overwritten (e.g., after merges/sanitization), and verify via git
  diff/log before proceeding.

### 2.2. How Augment Should Apply Other Rules

1. **Discover**: Always load the set of rule documents from `/.augment/rules/` (now `docs/guides/ai-agent/`) at the start of a task.
2. **Classify Applicability**:
    - Filter rules by `type` and `scope` (if present). Treat `always_apply` rules as globally applicable unless a more specific rule overrides them.
    - Consider `agent_requested` rules when the task involves agent behavior, planning, or output formatting.
3. **Prioritize**:
    - Prefer higher-specificity rules (a rule that names a file/path or task scope wins over a global preference).
    - When rules conflict, prefer (in order): explicit task instruction > rule with higher `priority` (numeric) > more specific `scope` > `always_apply`
      default.
    - If equal specificity and conflict remains, pause and ask the user for resolution.
4. **Apply and Document**:
    - For every non-trivial change, list which rules were consulted and which were applied in the implementation notes (e.g., `docs/updates/` entry or PR
      description).
    - If a rule was intentionally not applied (e.g., to avoid regressions), state the reason.

### 2.3. Recommended Metadata for Rule Files

To make rules easy to evaluate programmatically, include a short frontmatter block in each rule with the following useful fields:

- `name`: short human-friendly name (optional)
- `type`: one of `always_apply`, `agent_requested`, `informational`
- `description`: single-line summary
- `priority`: integer (higher = stronger preference). Default: `0` for neutral
- `scope`: optional glob or short description of what the rule targets (e.g., `src/**`, `docs/**`, `git-*`, `planning-flow`)
- `examples`: short examples of how to apply the rule (optional)
- `cross_reference`: list of other rule filenames this rule builds on or expects
- `apply_when`: optional short predicate describing when the rule should be considered (e.g., `task_type == "refactor"`)

### 2.4. Enforcement & Transparency

- Agents should add a single-line note to the PR description or `docs/updates/` entry summarizing: "Rules consulted: [list] — Rules applied: [list] —
  Overrides: [list with rationale]".
- When a numeric `priority` field is present, include it in the summary to aid reviewers.

### 2.5. Minimal Checklist for Rule Authors

When creating or editing a rule file, include:

- Frontmatter with `type`, `description`, and optional `priority` and `scope`.
- At least one short example of application.
- Cross-reference to related rules (if applicable).

### 2.6. Quality and Safety Notes

- Do not modify other rule files without documenting the reason in `docs/updates/` and a clear test or review step.
- Prefer conservative change: if unsure whether a rule applies, prefer asking the user rather than making silent overrides.

## 3. Examples

### Example Frontmatter (recommended)

```markdown
---
# name: "Testing conventions"
# type: "agent_requested"
# description: "Testing file locations and naming"
# priority: 10
# scope: "tests/**"
# cross_reference: ["preferences.md", "documentation.md"]
# apply_when: "task_involves_tests == true"
---
```

### Examples of Coordinated Application

- When implementing new features that change public APIs, Augment MUST consult `documentation.md` for docs placement and `git.md` for commit message format.
  Document this in the `docs/updates/` entry.
- When writing tests, consult `testing.md` for naming/placement and `preferences.md` for logging of applied rules.
- For planning-driven work, follow `planning.md`'s stop/confirm tokens (`<<AWAIT_CONFIRM: ...?>>`) unless the user explicitly requests executing immediately.

## 4. Rationale / Justification

These general preferences and guidelines are crucial for maintaining a consistent development process, ensuring high code quality, and providing clear
instructions for the AI agent. By defining how rules are discovered, prioritized, and applied, we enhance the agent's effectiveness and transparency.

## 5. Related Information

This document cross-references other core rule files that define specific conventions for Git, testing, planning, and documentation, ensuring a holistic
approach to project governance.

# References

- [Documentation Conventions](./AGENT-RULE-Documentation-Conventions.md)
- [Git Commit & Branching Conventions](./AGENT-RULE-Git-Conventions.md)
- [Planning Protocol](./AGENT-GUIDE-Planning-Protocol.md)
- [Testing Conventions](./AGENT-RULE-Testing-Conventions.md)
- `docs/updates/README.md`