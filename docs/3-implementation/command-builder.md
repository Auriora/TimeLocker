---
title: "Implementation Guide: Command Builder"
id: "impl-command-builder"
type: [ implementation ]
status: [ approved ]
owner: "CLI Team"
last_reviewed: "01-11-2025"
tags: [implementation, cli]
links:
    tooling: []
---

# Implementation Guide: Command Builder

- **Owner**: CLI Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: Developers extending CLI command construction utilities

## 1. Purpose

Document the `CommandBuilder` utility that assembles CLI invocations from declarative command definitions. This guide explains the abstractions, usage patterns,
and error handling expectations for contributors adding or modifying commands.

## 2. Implementation Details

### 2.1 Core Concepts

The builder relies on three primary classes:

1. `CommandParameter` – Describes a single parameter/flag, including prefix, requirement, style, and positional index.
2. `CommandDefinition` – Captures the structure of a command, its parameters, and nested subcommands.
3. `CommandBuilder` – Consumes definitions to produce argument lists (`List[str]`).

### 2.2 Parameter Styles

- `SEPARATE`: Parameter and value split into distinct arguments (e.g., `--param value`).
- `JOINED`: Parameter and value combined with `=` (e.g., `--param=value`).
- `POSITIONAL`: Value only, used for ordered arguments.

### 2.3 Usage Example

```python
from utils.command_builder import CommandBuilder, CommandDefinition, CommandParameter, ParameterStyle

# Define the command structure
install_cmd = CommandDefinition(
    name="pkg",
    parameters=[
        CommandParameter("verbose", prefix="-", required=False, value_required=False),
        CommandParameter("config", required=False),
    ],
    subcommands={
        "install": CommandDefinition(
            name="install",
            parameters=[
                CommandParameter("package", position=0, style=ParameterStyle.POSITIONAL, required=True),
                CommandParameter("target", prefix="--", required=False),
            ]
        )
    }
)

builder = CommandBuilder(install_cmd)
cmd = (builder
       .command("install")
       .param("verbose")
       .param("package", "timelocker")
       .param("target", "prod")
       .build())
# Result: ['pkg', 'install', '-v', 'timelocker', '--target', 'prod']
```

### 2.4 Restic Example

```python
restic_command = CommandDefinition(
    name="restic",
    parameters=[CommandParameter("repo", prefix="-", required=True)],
    subcommands={
        "backup": CommandDefinition(
            name="backup",
            parameters=[
                CommandParameter("exclude", required=False),
                CommandParameter("iexclude", required=False),
                CommandParameter("tag", required=False),
            ]
        ),
        "restore": CommandDefinition(
            name="restore",
            parameters=[
                CommandParameter("target", required=True),
                CommandParameter("snapshot-id", required=True),
            ]
        ),
    }
)
```

### 2.5 Best Practices

- **Required Parameters**: Mark mandatory inputs (`required=True`) to surface `ValueError` when omitted.
- **Parameter Styles**: Choose the correct style for CLI conventions (`JOINED`, `SEPARATE`, `POSITIONAL`).
- **Reset Between Builds**: Use `builder.clear()` when reusing instances across commands.
- **Type Hints**: Encourage static analysis by annotating builder usage.

### 2.6 Error Handling

`CommandBuilder` raises `ValueError` when:

- Required parameters are missing.
- Parameters/subcommands are undefined.
- Values are omitted for parameters requiring them.

## 3. Usage Notes

- Integrate new `CommandDefinition` instances with CLI entry points (`typer` commands) to maintain separation between definition and execution.
- When building commands dynamically, ensure options that imply specific flags are handled via helper methods rather than mutating definitions at runtime.
- Maintain unit tests for `CommandBuilder` behaviours (see `tests/TimeLocker/cli/test_cli_helpers.py`).

## 4. Change Log

- 01-11-2025: Converted to implementation template; clarified examples and best practices.
- 19-12-2024: Initial guide authored.

# References

- CLI hierarchy reference: `docs/reference/timelocker-cli-command-hierarchy.md`
- Credential workflows: `docs/guides/user/repository-management-guide.md`
