---
title: "Reference Documentation"
doc_type: reference
id: "RM-013"
type: [ readme ]
status: active
owner: "Auriora Team"
last_reviewed: 2026-07-18
tags: [readme, reference]
links:
  tooling: []
---

# Reference Documentation

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 27-10-2023

## 1. Purpose

**When to use this template**: This folder contains reference materials that provide detailed information on specific topics, such as tooling, APIs, or
licensing. These documents are typically stable and serve as authoritative sources of truth.
**Location**: `docs/reference/`

## 2. What Belongs Here?

- Documentation for project-specific tools and utilities.
- API specifications or data schemas.
- Licensing information and compliance guidelines.

## Available Reference Documents

### API References
- [Backup Operations API Reference](backup-operations-api.md) - Complete API documentation for backup orchestration
- [Recovery Operations API Reference](recovery-operations-api.md) - Complete API documentation for recovery operations
- [Recovery Operations Models Reference](recovery-operations-models-reference.md) - Data models for recovery operations

### Guides and Specifications
- [Repository URI Guide](repository-uri-guide.md) - Guide to repository URI formats
- [TimeLocker CLI Command Hierarchy](timelocker-cli-command-hierarchy.md) - CLI command structure
- [Repository Orientation and Change Map](repo-orientation-and-change-map.md) - CLI map, subsystem map, and code-change starting points

## 3. What Does NOT Belong Here?

- Step-by-step guides (see `../guides/`).
- Architectural decisions (see `../2-architecture/`).
- Chronological implementation history; use Git commits and pull requests.

## 4. Usage Notes

- **Checklist for Authors**:
    - [ ] Fill in all placeholder values (e.g., `[Name or Team]`).
    - [ ] Delete this `Usage Notes` section before publishing.
    - [ ] Ensure the document is linked from the relevant `README.md` file.

- **Naming Convention**: N/A for this file.

## 5. Available Templates

- Use the central [durable-document template](../templates/durable-document.md)
  for current reference material.

# References

- Link to additional resources, specs, or tickets
