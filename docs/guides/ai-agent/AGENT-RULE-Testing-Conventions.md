---
title: Testing conventions
doc_type: rule
type: agent_requested
name: Testing conventions
priority: 25
scope: tests/**
description: Pytest placement, naming, scope, and evidence conventions for TimeLocker.
cross_reference: [AGENT-GUIDE-General-Preferences.md, AGENT-GUIDE-Coding-Standards.md]
apply_when: task_involves_tests == true
owner: Auriora Team
status: active
last_reviewed: 2026-07-18
---

# Testing Conventions

## Purpose

Keep TimeLocker's pytest suite discoverable, behavior-focused, and consistent
with the configuration in `pyproject.toml`.

## Required Practices

- Put tests under `tests/`. Name files `test_*.py` or `*_test.py`, classes
  `Test*`, and functions `test_*`, matching pytest discovery configuration.
- Mirror the source or feature area where practical. Use existing `unit`,
  `integration`, `security`, `filesystem`, `backup`, `restore`, `monitoring`,
  and other declared markers rather than inventing unregistered markers.
- Test public behavior and meaningful failure paths. Prefer real value objects,
  temporary paths, and narrow fakes over mocking internal implementation
  details.
- Keep network, platform, slow, stress, and end-to-end behavior explicitly
  marked and isolated from focused unit validation.
- For a changed slice, run the narrowest relevant tests first. Before closure
  or release, run the full configured suite unless the active spec records a
  justified waiver and residual risk.
- Do not lower the coverage gate or weaken assertions to make a change pass.
  `pyproject.toml` is authoritative for the current 50 percent suite threshold.
- Record the command and result in the active spec, commit, pull request, CI
  run, or linked issue when evidence is required.

## Common Commands

```bash
pytest tests/path/to/test_module.py
pytest -m unit
pytest
```

The configured `pytest` command already enables coverage, strict markers,
timeouts, and reports. Use `--no-cov` only for a quick diagnostic run and never
as final suite evidence.

## References

- [General Preferences](./AGENT-GUIDE-General-Preferences.md)
- [Coding Standards](./AGENT-GUIDE-Coding-Standards.md)
- Repository-root `pyproject.toml`
- [`docs/4-testing/`](../../4-testing/README.md)
