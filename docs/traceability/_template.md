---
title: "Traceability: {{title}}"
id: "trace-{{id}}"
type: [ traceability ]
status: [ draft | in_review | approved ]
owner: "{{owner}}" # e.g., QA Team, Project Manager
last_reviewed: "{{DD-MM-YYYY}}"
tags: [traceability, quality, tag1, tag2] # Practical tags for organization and search
links:
  tooling: [ruff, mypy, bandit]
---

# Traceability: {{title}}

- **Owner**: {{owner}} # e.g., QA Team, Project Manager
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [e.g., QA Team, Developers, Project Managers, Stakeholders]

## 1. Purpose

Describe the goal of this traceability document. For example, "This document traces all user-facing requirements to their corresponding design documents,
implementation tasks, and test cases." Clearly state the objective and scope of this traceability document.

## 2. Scope

Define what this document covers and does not cover. For instance, "This matrix covers all functional requirements for the v2.0 release."

## 3. Traceability Matrix

Purpose: Ensure every requirement is covered by design/architecture elements, implemented code, and validated by tests.

| Requirement ID | Requirement Title   | Design/ADR/UXF Links | Implementation Links | Test Case IDs | Notes       |
|----------------|---------------------|----------------------|----------------------|---------------|-------------|
| SRS-000        | Example Requirement | ADR-0001, UXF-0001   | module/path          | TC-ABC-001    | Example row |

## 4. Maintenance

- Update when adding/changing requirements, ADRs/UXFs, implementations, or tests.
- For each row, provide deep links (file paths or URLs) where possible.
  Explain how and when this document should be updated. For example, "This document must be updated as part of the definition of done for any new requirement."

<!-- Add more numbered sections as needed, e.g., ## 5. [Another Section Title] -->

# References

- Link to additional resources, specifications, or related tickets.
