---
title: Coding standards for AI-generated code
doc_type: guide
type: always_apply
name: Coding standards for AI-generated code
priority: 100
scope: src/**
description: Mandatory Python standards for AI-generated or modified TimeLocker code.
cross_reference: [AGENT-GUIDE-General-Preferences.md, AGENT-RULE-Testing-Conventions.md]
apply_when: always
owner: Auriora Team
status: active
last_reviewed: 2026-07-18
---

# Coding Standards for AI-Generated Code

## Purpose

Keep changes consistent with TimeLocker's Python 3.12+ package, public backup
interfaces, Typer CLI, and existing repository patterns.

## Required Practices

- Read the relevant requirements in `docs/1-requirements/`, architecture in
  `docs/2-architecture/`, active spec context, and nearby implementation before
  changing behavior.
- Use Python naming conventions, type annotations on new or changed public
  interfaces, and focused docstrings where behavior or constraints are not
  obvious. Do not add comments that merely restate code.
- Preserve separation between CLI orchestration, service/domain behavior,
  repository/storage adapters, configuration, and monitoring integrations.
- Prefer a dependency already declared in `pyproject.toml` or a project-standard
  library over a custom implementation. Do not infer a web framework, database
  layer, or distributed system that TimeLocker does not have.
- Keep compatibility seams unless the active spec explicitly authorizes their
  removal. Treat CLI commands and documented Python interfaces as public.
- Raise specific exceptions with useful context and use exception chaining when
  translating an error. Do not catch exceptions only to suppress them.
- Use the standard `logging` package and the repository's existing telemetry
  helpers where they add operational value. Never log credentials, repository
  passwords, tokens, command secrets, or sensitive path contents.
- Avoid unnecessary abstraction, duplication, global mutable state, and magic
  values. Name constants when a value has domain meaning.
- Add or update tests for changed behavior according to
  [Testing Conventions](./AGENT-RULE-Testing-Conventions.md).

## Example

```python
def require_non_negative(value: int, *, field: str) -> int:
    """Return value when valid; otherwise raise a contextual error."""
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value
```

## References

- [General Preferences](./AGENT-GUIDE-General-Preferences.md)
- [Testing Conventions](./AGENT-RULE-Testing-Conventions.md)
- [`docs/1-requirements/`](../../1-requirements/README.md)
- [`docs/2-architecture/`](../../2-architecture/README.md)
