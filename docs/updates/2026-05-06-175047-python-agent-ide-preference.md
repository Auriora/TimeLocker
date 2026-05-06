---
title: "Update: Python Agent IDE Preference"
id: "update-2026-05-06-175047-python-agent-ide-preference"
type: [ update ]
status: [ approved ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, ai-agent, python-agent-ide, mcp]
links:
  tooling: [python-agent-ide]
---

# Update: Python Agent IDE Preference

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: AI agents and maintainers
- **Related**: `AGENTS.md`, `docs/guides/ai-agent/AGENT-GUIDE-Operational-Best-Practices.md`
- **Scope**: root agent instructions and centralized AI agent guidance

## 1. Purpose

Record the documentation update that makes Python Agent IDE the preferred agent workflow for repository exploration and validation support.

## 2. Summary

The root `AGENTS.md` now calls out the preference for the Python Agent IDE plugin, skills, and MCP tools. The centralized operational guide also documents the
same preference as the source-of-truth behavior for AI agents.

## 3. Implementation Notes

- Updated `AGENTS.md` so agents see the preference at task start.
- Updated `docs/guides/ai-agent/AGENT-GUIDE-Operational-Best-Practices.md` so the centralized rule set remains authoritative.
- Clarified that slow responses, partial results, and timeouts should be recorded and narrowed or retried before falling back.
- Validation: documentation-only change; no test suite run.

## 4. Documentation & Links

- `AGENTS.md`
- `docs/guides/ai-agent/AGENT-GUIDE-Operational-Best-Practices.md`

# References

- Python Agent IDE plugin and MCP tooling
