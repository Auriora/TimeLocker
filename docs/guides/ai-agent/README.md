---
title: "AI Agent Rules and Guides"
id: "AI-AGENT-README"
type: [ readme, agent-rules ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [readme, ai-agent, rules, guides]
links:
  tooling: []
---

# AI Agent Rules and Guides

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY

## 1. Purpose

This folder serves as the centralized repository for all AI Agent rules, operational guides, and configuration details. It replaces the hidden `.agents/rules/`
directory to improve discoverability, maintainability, and consistency with other project documentation.

## 2. What Belongs Here?

- Specific operational rules or instructions for AI agents.
- Broader guides on agent behavior, principles, or setup.
- Configuration details or parameters related to agent operation.

## 3. What Does NOT Belong Here?

- General project documentation (see `docs/`).
- Implementation details of the agent's core logic (see `docs/3-implementation/`).
- Architectural decisions not directly related to agent rules (see `docs/2-architecture/`).

## 4. Usage Notes

- **Checklist for Authors**:
    -   [ ] Fill in all placeholder values (e.g., `{{owner}}`, `DD-MM-YYYY`).
    -   [ ] Ensure the `type` property in the frontmatter uses one of the allowed values (`agent_requested`, `always_apply`).
    -   [ ] Ensure the document is linked from relevant `README.md` files or other guides.

- **Naming Convention**: `<type>-<description>.md`
    - **AGENT-RULE**: For specific operational rules or instructions (e.g., `AGENT-RULE-Git-Conventions.md`).
    - **AGENT-GUIDE**: For broader guides on agent behavior or principles (e.g., `AGENT-GUIDE-Planning-Protocol.md`).
    - **AGENT-CONFIG**: For configuration details or parameters.
    - For sequenced rules, a numeric prefix can be used: `[number]-AGENT-RULE-<description>.md`.

## 5. Available Templates

- `_template.md`: A generic template for AI Agent rules and guides.

# References

- Link to relevant AI Agent documentation or external resources.
