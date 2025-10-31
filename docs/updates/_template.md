---
title: "Update: {{title}}"
id: "update-{{id}}"
type: [ update ]
status: [ draft | in_review | approved ]
owner: "{{owner}}" # e.g., Author, Agent
last_reviewed: "{{DD-MM-YYYY}}"
tags: [update, tag1, tag2] # Practical tags for organization and search
links:
  tooling: [ruff, mypy, bandit]
---

# Update: {{title}}

- **Owner**: {{owner}} # e.g., Author, Agent
- **Created Date**: DD-MM-YYYY
- **Audience**: [e.g., Developers, Stakeholders, Team Members]
- **Related**: PR/Issue links/Document
- **Scope**: [e.g., root, specific service]

## 1. Purpose

Describe the change, reasoning, and any alternatives considered. Clearly state the objective and scope of this update document.

## 2. Summary

Describe the change, reasoning, and any alternatives considered.

## 3. Implementation Notes

- Key code paths or scripts updated
- Testing performed (include commands)
- Follow-up tasks, if any

## 4. Documentation & Links

- Updated docs references
- Additional resources or external specs

<!-- Add more numbered sections as needed, e.g., ## 5. [Another Section Title] -->

# References

- Link to additional resources, specifications, or related tickets.
