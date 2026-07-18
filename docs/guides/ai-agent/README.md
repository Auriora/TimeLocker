---
title: AI agent rules and guides
doc_type: reference
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# AI Agent Rules and Guides

This directory is the single source of detailed agent instructions for
TimeLocker. Root `AGENTS.md` only routes agents here; editor-specific settings
must not duplicate these rules.

## Rule Order

1. Explicit user and platform instructions.
2. Higher numeric `priority` in a matching rule.
3. More specific `scope`.
4. General always-apply guidance.

If equally authoritative rules still conflict, stop and ask for resolution.

## Current Rules

- [Coding Standards](./AGENT-GUIDE-Coding-Standards.md)
- [General Preferences](./AGENT-GUIDE-General-Preferences.md)
- [Operational Best Practices](./AGENT-GUIDE-Operational-Best-Practices.md)
- [Planning Protocol](./AGENT-GUIDE-Planning-Protocol.md)
- [Documentation Conventions](./AGENT-RULE-Documentation-Conventions.md)
- [Git Conventions](./AGENT-RULE-Git-Conventions.md)
- [Testing Conventions](./AGENT-RULE-Testing-Conventions.md)

## Authoring Rules

- Use `AGENT-RULE-<description>.md` for mandatory task-specific rules and
  `AGENT-GUIDE-<description>.md` for broader operating guidance.
- Include `title`, `doc_type`, `type`, `priority`, `scope`, `description`,
  `apply_when`, `owner`, `status`, and `last_reviewed` frontmatter.
- Link real filenames in `cross_reference`; do not use shorthand aliases.
- Start from the central
  [agent-instruction template](../../templates/agent-instruction.md).
- Record the reason and validation for a rule change in the active spec, commit,
  pull request, CI run, or linked issue.

General project documentation belongs elsewhere under `docs/`. Runtime design
belongs under `docs/2-architecture/` or `docs/3-implementation/`.
