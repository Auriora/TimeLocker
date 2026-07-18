# AGENTS

This repository uses centralized agent instructions located in `docs/guides/ai-agent/`.

- The rule files in `docs/guides/ai-agent/` are the single source of truth and take precedence over any guidance elsewhere in the repo.
- To avoid duplication or conflicts, this file intentionally does not restate operational commands, workflows, or protocols.

For general project context and developer documentation, refer to:

- `README.md` (project overview, commands, architecture)
- `docs/` (project documentation, active specifications, agent workflows, and implementation history)
- `CLAUDE.md` (editor-specific tips, if applicable)

If you are implementing or running agents/tools:

- Load `docs/guides/ai-agent/` at task start and follow the highest-priority instructions found there.
- Scan [`docs/specs/`](docs/specs/README.md) at task start. For complex,
  cross-cutting, migration, or governance-sensitive work, use the Spec
  Lifecycle Manager workflow and the active package as the implementation
  contract. Durable docs remain the current-state authority.
- Prefer the Python Agent IDE plugin, its skills, and its MCP tools for repository exploration, context gathering, impact analysis, diagnostics, and test
  targeting. Keep using that workflow even when it is slow, returns partial results, or encounters timeouts; record any limitations and only fall back when the
  plugin or requested capability is unavailable.
- Record task-scoped implementation evidence in the active spec, commit, pull
  request, CI run, or linked issue. Do not create standalone update diaries
  under `docs/`.

This document is intentionally minimal to prevent divergence from `docs/guides/ai-agent/`. Consult those rule files first, and prefer updating them over this
file when behavior or priorities change.
