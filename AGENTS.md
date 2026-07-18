# AGENTS

This repository uses two complementary authorities:

- `CHARTER.md` is the source of truth for the project mandate, boundaries,
  governance, and measures of success.
- The rule files in `docs/guides/ai-agent/` are the source of truth for agent
  behavior, operational commands, workflows, and protocols. They take
  precedence when agent instructions conflict.

This file is intentionally a minimal router and does not duplicate either
authority.

For general project context and developer documentation, refer to:

- `CHARTER.md` (project mandate, boundaries, governance, success measures)
- `README.md` (project overview, commands, architecture)
- `docs/` (project documentation, active specifications, agent workflows, and implementation history)
- `CLAUDE.md` (editor-specific tips, if applicable)

If you are implementing or running agents/tools:

- Read `CHARTER.md` at task start and confirm that the requested work fits the
  current mandate and boundaries. Route out-of-scope proposals for an explicit
  project-scope decision before implementation.
- Load `docs/guides/ai-agent/` at task start and follow the highest-priority instructions found there.
- Scan [`docs/specs/`](docs/specs/README.md) at task start. For complex,
  cross-cutting, migration, or governance-sensitive work, use the Spec
  Lifecycle Manager workflow and the active package as the implementation
  contract. Durable docs remain the current-state authority.
- For code, documentation, architecture, security, test-quality, or overall
  repository reviews, use the repository-local skill at
  `.agents/skills/review-timelocker/SKILL.md`.
- Prefer the Python Agent IDE plugin, its skills, and its MCP tools for repository exploration, context gathering, impact analysis, diagnostics, and test
  targeting. Keep using that workflow even when it is slow, returns partial results, or encounters timeouts; record any limitations and only fall back when the
  plugin or requested capability is unavailable.
- Record task-scoped implementation evidence in the active spec, commit, pull
  request, CI run, or linked issue. Do not create standalone update diaries
  under `docs/`.

When guidance changes, update the owning authority: `CHARTER.md` for project
direction, `docs/guides/ai-agent/` for agent behavior, and this file only for
routing.
