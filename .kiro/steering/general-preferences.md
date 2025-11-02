---
inclusion: always
---

# General Project Preferences

**Priority**: 50  
**Scope**: .*  
**Description**: General project preferences and guidance for coordinating and applying other rules.

## Core Principles

- Code must follow SOLID and DRY principles.
- Code reviews must be thorough with refactoring suggestions to improve code quality.
- Prefer direct implementation to extensive planning and analysis phases where appropriate.
- Always double-check during testing or implementation if any changes have been lost or overwritten (e.g., after merges/sanitization), and verify via git diff/log before proceeding.

## Quality and Safety Notes

- Do not modify other rule files without documenting the reason in `docs/updates/` and a clear test or review step.
- Prefer conservative change: if unsure whether a rule applies, prefer asking the user rather than making silent overrides.

## Rule Application Guidelines

When working with multiple steering files:

1. **Discover**: Always load the set of rule documents from `.kiro/steering/` at the start of a task.
2. **Classify Applicability**: Filter rules by scope and inclusion type. Treat `always` inclusion rules as globally applicable unless a more specific rule overrides them.
3. **Prioritize**: When rules conflict, prefer (in order): explicit task instruction > rule with higher priority > more specific scope > always inclusion default.
4. **Apply and Document**: For every non-trivial change, list which rules were consulted and which were applied in implementation notes.

## Enforcement & Transparency

- Agents should add a single-line note to the PR description or `docs/updates/` entry summarizing: "Rules consulted: [list] — Rules applied: [list] — Overrides: [list with rationale]".
- When a numeric priority field is present, include it in the summary to aid reviewers.