---
title: "Requirements: {{title}}"
id: "req-{{id}}"
type: [ requirements ]
status: [ draft | in_review | approved ]
owner: "{{owner}}" # e.g., Product Owner, Requirements Team
last_reviewed: "{{DD-MM-YYYY}}"
tags: [requirements, functional, non-functional, tag1, tag2] # Practical tags for organization and search
links:
  tooling: [ruff, mypy, bandit]
---

# Requirements: {{title}}

- **Owner**: {{owner}} # e.g., Product Owner, Requirements Team
- **Status**: [Draft | In Review | Approved]
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [e.g., Product Owners, Engineering Teams, QA, Stakeholders]

## 1. Purpose

[Provide a high-level summary of the product or feature. Describe its purpose, the problem it solves, and its business value.]
Clearly state the objective and scope of this requirements document.

## 2. Functional Requirements

1. **FR-001**: [The system MUST/SHOULD... Describe a specific behavior, user interaction, or system response.]
2. **FR-002**: [Another functional requirement.]

<!-- Add more functional requirements as needed. -->

## 3. Non-Functional Requirements

- **Performance**: [e.g., API endpoints must respond within 200ms under 1000 RPS.]
- **Security**: [e.g., All sensitive data must be encrypted at rest using AES-256.]
- **Maintainability**: [e.g., Code must adhere to the established style guide.]
- **Compatibility**: [e.g., The system must be compatible with Chrome, Firefox, and Safari.]

<!-- Add more non-functional requirements as needed. -->

## 4. Acceptance Criteria

- [ ] [A specific, testable scenario and its expected outcome.]
- [ ] [Another scenario and its expected outcome.]

<!-- Add more acceptance criteria as needed. -->

## 5. Dependencies

- [List any external systems, services, teams, or decisions required for this work.]

<!-- Add more dependencies as needed. -->

<!-- Add more numbered sections as needed, e.g., ## 6. [Another Section Title] -->

# References

- Link to additional resources, specifications, or related tickets.
