---
type:        "agent_requested"
name:        "Operational Best Practices for AI Agents"
priority:    40
scope:       ".*"
description: "Guidelines for AI agent operational behavior, including SRS alignment and tool usage."
cross_reference: ["AGENT-GUIDE-Coding-Standards.md"]
apply_when:   "always"
---

# AI Agent Rule/Guide: Operational Best Practices for AI Agents

- **Type**: agent_requested
- **Priority**: 40
- **Scope**: .*
- **Description**: Guidelines for AI agent operational behavior, including SRS alignment and tool usage.
- **Cross-Reference**: AGENT-GUIDE-Coding-Standards.md
- **Apply When**: always

## 1. Purpose

This document outlines the operational best practices and meta-rules for AI agents working within the `admin-assistant` project. Its purpose is to ensure
consistent, transparent, and high-quality agent behavior, particularly concerning tool usage, code modifications, error handling, and alignment with project
documentation.

## 2. Rule/Guideline Details

### 2.1. AI Agent Operational Best Practices

- **Tool-Driven Exploration**: Always use available codebase exploration tools (semantic search, file search, directory listing, etc.) to gather information
  before making assumptions or generating code.
- **Minimal and Contextual Edits**: When editing files, specify only the minimal code necessary for the change, using context markers to avoid accidental code
  removal. Never output unchanged code unless necessary for context.
- **Error Handling**: Attempt to fix linter or syntax errors if the solution is clear. After three unsuccessful attempts, escalate to the user.
- **Command Line Usage**: Use non-interactive flags for shell commands and avoid commands requiring user interaction unless instructed. Run long-running jobs in
  the background.
- **Query Focus**: When a `<most_important_user_query>` is present, treat it as the authoritative query and ignore previous queries.
- **Clarification**: Always ask clarifying questions if requirements are ambiguous. Prefer tool-based discovery over user queries when possible.
- **Process Transparency**: Justify all actions taken and explain them in the context of the user's request.
- **Security**: Never output, log, or expose sensitive information in any user-facing message or code output.
- **Documentation Consistency**: Always update `docs/guides/ai-agent/AGENT-GUIDE-Operational-Best-Practices.md` (this file) when asked to update AI Guidelines
  to ensure documentation remains current and consistent.
- **Command Output Analysis**: Read command output thoroughly to the end before interpreting results. Avoid making premature assumptions about errors or success
  states. Always verify the exact location and nature of issues by analyzing the complete output rather than jumping to conclusions based on partial
  information.

### 2.2. SRS and Design Alignment

- All AI-generated code and documentation must align with the current Software Requirements Specification (SRS) in `docs/1-requirements/` and the design
  documentation in `docs/2-architecture/`.
- The SRS defines the authoritative requirements, use cases, and constraints. The design documentation provides architectural, data model, and feature-specific
  design details. Any generated code must directly support and not contradict the SRS or design documentation.
- When the SRS or design documentation is updated, these guidelines and all generated code must be reviewed for continued compliance.

### 2.3. Project-Specific Notes

- This file must be referenced in all AI code generation settings and updated as new requirements arise.
- All code must comply with Microsoft 365 API usage policies and data privacy requirements.

## 3. Examples

```
# Example of tool-driven exploration before coding
# User: "Implement feature X"
# Agent: (runs `find_files` for relevant modules, `grep` for existing patterns)
# Agent: "Found existing patterns in Y and Z. Proceeding with implementation based on these."

# Example of minimal edit
# User: "Change line 10 of file.py to 'new_value'"
# Agent: (outputs only the changed line with context markers, not the whole file)
```

## 4. Rationale / Justification

These operational best practices are critical for ensuring that AI agents function effectively, safely, and in alignment with project goals. By providing clear
directives on how to interact with the codebase, handle errors, and adhere to documentation, we enhance the reliability and trustworthiness of AI-generated
contributions.

## 5. Related Information

- **Project Directory Structure & Frameworks**: The project uses a specific structure and frameworks (Flask, SQLAlchemy, Pytest) detailed in
  `IMPL-Code-Structure.md`.
- **Core Layer and Data Access Guidelines**: Specific architectural patterns for the `core/` module are outlined in `IMPL-Code-Structure.md`.
- **Migration and Shell Guidelines**: Best practices for database migrations (Alembic) and shell command usage (preferring Bash) are detailed in
  `IMPL-Migration-Implementation-Summary.md`.

# References

- [General Preferences](./AGENT-GUIDE-General-Preferences.md)
- [Coding Standards for AI-Generated Code](./AGENT-GUIDE-Coding-Standards.md)
- [IMPL: Code Structure Overview](../../3-implementation/IMPL-Code-Structure.md)
- [IMPL: Database Migration Implementation Summary](../../3-implementation/IMPL-Migration-Implementation-Summary.md)
- `docs/1-requirements/` (for SRS documentation)
- `docs/2-architecture/` (for design documentation)