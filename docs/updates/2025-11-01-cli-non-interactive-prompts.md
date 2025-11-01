---
title: "Update: CLI prompt fallback for non-interactive streams"
id: "update-cli-non-interactive-prompts"
type: [ update ]
status: [ approved ]
owner: "AI Agent"
last_reviewed: "01-11-2025"
tags: [update, cli]
links:
  tooling: [pytest]
---

# Update: CLI prompt fallback for non-interactive streams

- **Owner**: AI Agent
- **Created Date**: 01-11-2025
- **Audience**: Developers
- **Related**: N/A
- **Scope**: src/TimeLocker/cli.py

## 1. Purpose

Prevent Rich password prompts from hanging when the CLI runs under non-interactive harnesses such as Typer's `CliRunner`. Ensures automated tests and scripted
workflows can provide credential input without a TTY.

## 2. Summary

Introduced a Rich console input shim that detects non-interactive streams and falls back to plain line reads while preserving the existing behaviour for real
TTY sessions. Applied the shim at the Rich `Console` class level so all prompts, including those instantiated internally by Rich, honour the fallback. This
allows prompts within `repos credentials set` to function during integration tests that feed answers via pipes.

## 3. Implementation Notes

- Key updates in `src/TimeLocker/cli.py`: added `_stream_is_interactive` helper and replaced Rich's `Console.input` globally with a non-interactive aware
  wrapper.
- Testing: `pytest tests/TimeLocker/integration/test_repos_credentials_command_usage.py -q`
- Follow-up tasks: None.
- Rules consulted: AGENT-GUIDE-Coding-Standards (priority 100), AGENT-RULE-Testing-Conventions (priority 25).

## 4. Documentation & Links

- No additional documentation updates required.

# References

- None.
