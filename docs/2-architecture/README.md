---
title: "Architecture Documentation"
doc_type: reference
id: "RM-004"
type: [ readme ]
status: active
owner: "Auriora Team"
last_reviewed: 2026-07-18
tags: [ readme, architecture ]
links:
    tooling: [ ]
---

# Architecture Documentation

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 2025-11-07

## 1. Purpose

**When to use this template**: This folder is used to document system structure, integration points, and architectural decisions. It serves as the authoritative
source for diagrams, Architecture Decision Records (ADRs), and infrastructure layouts.
**Location**: `docs/2-architecture/`

## 2. What Belongs Here?

- Architecture Decision Records (ADRs).
- System component diagrams and data flows.
- Deployment topologies and infrastructure notes.

## 3. What Does NOT Belong Here?

- Low-level implementation details (see `../3-implementation/`).
- Test strategies (see `../4-testing/`).
- Day-to-day change logs; use Git commits and pull requests.

## 4. Usage Notes

- **Checklist for Authors**:
    - [ ] Fill in all placeholder values (e.g., `[Name or Team]`).
    - [ ] Delete this `Usage Notes` section before publishing.
    - [ ] Ensure the document is linked from the relevant `README.md` file.

- **Naming Convention**: `<type>-<description>.md` (e.g., `ADR-001-Database-Choice.md`, `HLD-System-Overview.md`).

## 4. Available Documents

See [README.design.md](./README.design.md) for a complete index of architecture documents including:
- Design overview and technical architecture
- Component breakdown and data models
- Security considerations and scalability
- API specifications and references

## 5. Available Templates

- Use the central [durable-document template](../templates/durable-document.md)
  for architecture and the [decision-record template](../templates/decision-record.md)
  for accepted architectural choices.

## 6. References

- [Design Index](./README.design.md) - Complete architecture document index
- [Implementation](../3-implementation/README.md) - Implementation details
- [Spec Packages](../specs/README.md) - Active governed changes
