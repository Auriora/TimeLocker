---
type:        "agent_requested"
name:        "Documentation conventions"
priority:    20
scope:       "docs/**"
description: "This rule provides a standardized documentation format and policy for all projects."
cross_reference: ["preferences.md"]
apply_when:   "task_changes_documentation == true"
---

# AI Agent Rule/Guide: Documentation Conventions

- **Type**: agent_requested
- **Priority**: 20
- **Scope**: docs/**
- **Description**: This rule provides a standardized documentation format and policy for all projects.
- **Cross-Reference**: preferences.md
- **Apply When**: task_changes_documentation == true

## 1. Purpose

This rule establishes standardized documentation conventions and policies for all projects. It guides the AI agent on where documentation should reside, how it
should be structured, and best practices for maintaining its quality and consistency.

## 2. Rule/Guideline Details

### 2.1. MUST: Use the Repo's Documentation Structure

All documentation MUST live under `docs/` and follow the established structure:

```
docs/
├── README.md                           # Documentation hub landing page
├── _template/                          # Templates for all doc types
│   ├── _template.md
│   ├── _template.README.md
│   └── README.md
├── 0-project-management/               # Project tracking and management
│   ├── tasks-to-issues-map.md
│   └── README.md
├── 1-requirements/                     # Requirements and specifications
│   ├── _template.md
│   └── README.md
├── 2-architecture/                     # Architecture and design docs
│   ├── _template.md
│   ├── overview.md
│   ├── system-architecture.md
│   └── README.md
├── 3-implementation/                   # Implementation details
│   ├── _template.md
│   ├── command-builder.md
│   └── README.md
├── 4-testing/                          # Testing documentation
│   ├── _template.md
│   ├── test-plan.md
│   └── README.md
├── guides/                             # User and developer guides
│   ├── user/                           # End-user documentation
│   ├── developer/                      # Developer/contributor docs
│   ├── ai-agent/                       # AI agent instructions
│   └── README.md
├── plans/                              # Implementation plans
│   ├── _template.md
│   └── README.md
├── processes/                          # Process documentation
│   ├── _template.md
│   ├── version-management.md
│   └── README.md
├── proposals/                          # Design proposals
│   ├── _template.md
│   └── README.md
├── reference/                          # Reference documentation
│   ├── _template.md
│   └── README.md
├── reports/                            # Status and analysis reports
│   ├── _template.md
│   ├── _template.code-quality.md
│   ├── _template.coverage.md
│   └── README.md
├── updates/                            # Implementation update logs
│   ├── _template.md
│   ├── index.md
│   └── README.md
├── traceability/                       # Traceability matrices
│   ├── _template.md
│   └── README.md
└── archive/                            # Historical documentation
    └── README.md
```

- Do NOT add documentation files outside `docs/`.
- Do NOT create ad-hoc directories like `docs/progress/`, `docs/architecture/`, `docs/tasks/`, or any other non-standard folders - use the established structure.

### 2.2. MUST: Write "What Was Implemented" Docs in `docs/updates`

Task-scoped implementation notes (often written by agents) MUST be placed in `docs/updates/`:

- File naming: `YYYY-MM-DD-descriptive-slug.md`.
- Use the template: `docs/updates/_TEMPLATE.md`.
- Add to the index: `docs/updates/index.md` (newest first).
- Optionally add a short entry to `CHANGELOG.md` linking to the update.
- See guidance: `docs/updates/README.md`.

These updates complement the CHANGELOG and should not duplicate full release notes.

### 2.3. SHOULD: Update the Right Page for the Right Change

- Requirements and specifications → `docs/1-requirements/`
- Architecture/service design changes → `docs/2-architecture/` (NOT `docs/architecture/`)
- Implementation details and code structure → `docs/3-implementation/`
- Testing documentation → `docs/4-testing/`
- User guides and tutorials → `docs/guides/user/`
- Developer/contributor guides → `docs/guides/developer/`
- AI agent instructions → `docs/guides/ai-agent/`
- Reference documentation (APIs, specs) → `docs/reference/`
- Implementation plans → `docs/plans/`
- Process documentation → `docs/processes/`
- Design proposals → `docs/proposals/`
- Status reports and analysis → `docs/reports/`
- Implementation update logs → `docs/updates/`
- Task and project tracking → `docs/0-project-management/` (NOT `docs/tasks/`)
- Traceability matrices → `docs/traceability/`
- Historical documentation → `docs/archive/`

### 2.4. MUST NOT: Duplicate Content

- One home per concept. Reference, don’t repeat.
- Do not copy parameter tables across multiple docs. The canonical source is `docs/reference/tools.md`.
- Do not place status/update narratives in concept/reference docs—use `docs/updates/`.

### 2.5. SHOULD: Maintain Cross-Links and Freshness

- When moving/renaming docs, update internal links in affected files.
- Add a "Last updated: <YYYY-MM-DD>" header to substantive docs.
- Prefer relative links within `docs/` (e.g., `../reference/tools.md`).

### 2.6. MAY: Archive Historical Documents

- Obsolete status/update or migration notes belong in `docs/archive/`.
- Do not add new content directly to `archive/`; move there only after consolidation.

### 2.7. PR Checklist (enforced by reviewers/agents)

-   [ ] If code behavior or APIs changed, updated relevant reference docs in `docs/reference/`
-   [ ] If requirements changed, updated `docs/1-requirements/`
-   [ ] If architecture changed, updated `docs/2-architecture/` (NOT `docs/architecture/`)
-   [ ] If implementation details changed, updated `docs/3-implementation/`
-   [ ] If testing approach changed, updated `docs/4-testing/`
-   [ ] If work was task-scoped, added an entry in `docs/updates/` with timestamp and updated `docs/updates/index.md`
-   [ ] If creating a status report, added to `docs/reports/` with timestamp
-   [ ] If tracking tasks, updated `docs/0-project-management/` (NOT `docs/tasks/`)
-   [ ] Updated `docs/README.md` if navigation/structure changed
-   [ ] Removed duplication and updated cross-links; added "Last updated" where applicable

### 2.8. Formatting & Style

- Markdown only. Prefer bullets and short paragraphs.
- Include examples and exact parameter names/types where helpful.
- Use code fences with languages for commands and snippets.
- Use PlantUML in Markdown for diagrams when appropriate.
- Provide docstrings for public APIs in code (PEP 257 style) with type hints.

### 2.9. Implementation Notes and Reports

**Updates (Implementation Logs)**

Task-scoped implementation notes (often written by agents) MUST be placed in `docs/updates/`:

- File naming: `YYYY-MM-DD-HHMMSS-descriptive-slug.md` (include timestamp for uniqueness).
- Use the template: `docs/updates/_template.md`.
- Add to the index: `docs/updates/index.md` (newest first).
- Optionally add a short entry to `CHANGELOG.md` linking to the update.
- See guidance: `docs/updates/README.md`.

**Reports (Status and Analysis)**

Status reports, progress summaries, and analysis documents MUST be placed in `docs/reports/`:

- File naming: `YYYY-MM-DD-HHMMSS-descriptive-slug.md` (include timestamp for uniqueness).
- Use the appropriate template from `docs/reports/`:
  - `_template.md` - Generic report template
  - `_template.code-quality.md` - Code quality reports
  - `_template.coverage.md` - Test coverage reports
  - `_template.security-review.md` - Security reviews
- See guidance: `docs/reports/README.md`.

**Key Distinction**:
- **Updates**: What was implemented, how it was done, technical details
- **Reports**: Status snapshots, metrics, analysis, findings

## 3. Examples

```markdown
---
# name: "Example Document"
# type: "agent_requested"
# description: "A brief description of the document."
# priority: 10
# scope: "docs/concepts/**"
# cross_reference: ["another-rule.md"]
# apply_when: "task_adds_new_concept == true"
---
```

## 4. Rationale / Justification

Adhering to a standardized documentation structure and policy is critical for maintaining a well-organized, discoverable, and consistent knowledge base. This
rule ensures that all project documentation is easily accessible, up-to-date, and contributes effectively to the project's overall understanding and
maintainability.

## 5. Related Information

This rule is cross-referenced with `preferences.md` for general project preferences and guidance on coordinating and applying other rules. It also implicitly
relates to all other documentation within the `docs/` directory.

# References

- [General Preferences](./AGENT-GUIDE-General-Preferences.md)
- [Documentation Conventions Steering](../../../.kiro/steering/documentation-conventions.md)
- `docs/updates/README.md`
- `docs/updates/index.md`
- `docs/reports/README.md`
- `CHANGELOG.md`