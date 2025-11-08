---
inclusion: always
---

# Operational Best Practices for AI Agents

**Priority**: 40  
**Scope**: .*  
**Description**: Guidelines for AI agent operational behavior, including SRS alignment and tool usage.

## AI Agent Operational Best Practices

- **Tool-Driven Exploration**: Always use available codebase exploration tools (semantic search, file search, directory listing, etc.) to gather information before making assumptions or generating code.
- **Minimal and Contextual Edits**: When editing files, specify only the minimal code necessary for the change, using context markers to avoid accidental code removal. Never output unchanged code unless necessary for context.
- **Error Handling**: Attempt to fix linter or syntax errors if the solution is clear. After three unsuccessful attempts, escalate to the user.
- **Command Line Usage**: Use non-interactive flags for shell commands and avoid commands requiring user interaction unless instructed. Run long-running jobs in the background.
- **Query Focus**: When a `<most_important_user_query>` is present, treat it as the authoritative query and ignore previous queries.
- **Clarification**: Always ask clarifying questions if requirements are ambiguous. Prefer tool-based discovery over user queries when possible.
- **Process Transparency**: Justify all actions taken and explain them in the context of the user's request.
- **Security**: Never output, log, or expose sensitive information in any user-facing message or code output.
- **Documentation Consistency**: Always update relevant documentation when asked to update AI Guidelines to ensure documentation remains current and consistent.
- **Documentation Placement**: All comprehensive documentation must be placed in `docs/`. Source folders (`src/`) may only contain minimal README files (1-3 sentences) that point to detailed documentation in `docs/`. See `documentation-conventions.md` for full policy.
- **Command Output Analysis**: Read command output thoroughly to the end before interpreting results. Avoid making premature assumptions about errors or success states. Always verify the exact location and nature of issues by analyzing the complete output rather than jumping to conclusions based on partial information.

## SRS and Design Alignment

- All AI-generated code and documentation must align with the current Software Requirements Specification (SRS) in `docs/1-requirements/` and the design documentation in `docs/2-architecture/`.
- The SRS defines the authoritative requirements, use cases, and constraints. The design documentation provides architectural, data model, and feature-specific design details. Any generated code must directly support and not contradict the SRS or design documentation.
- When the SRS or design documentation is updated, these guidelines and all generated code must be reviewed for continued compliance.

## Project-Specific Notes

- This file must be referenced in all AI code generation settings and updated as new requirements arise.
- All code must comply with data privacy requirements and security best practices.