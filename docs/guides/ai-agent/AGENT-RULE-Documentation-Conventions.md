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
├── index.md                      # Landing page (keep updated)
├── getting-started/quickstart.md # Setup in 5 minutes
├── concepts/                     # Core ideas
│   ├── canonical-events.md
│   ├── categories.md
│   └── CATEGORY_MANAGEMENT.md
├── reference/                    # Source of truth for APIs/specs
│   ├── tools.md
│   └── activitywatch-integration.md
├── architecture/implementation.md# Technical details & design
├── developer/                    # Contributor/ops docs
│   ├── best-practices.md
│   └── logging-and-health.md
├── updates/                      # "What Was Implemented" docs
│   ├── README.md
│   ├── _TEMPLATE.md
│   └── index.md
└── archive/                      # Historical docs only
```

- Do NOT add documentation files outside `docs/`.

### 2.2. MUST: Write "What Was Implemented" Docs in `docs/updates`

Task-scoped implementation notes (often written by agents) MUST be placed in `docs/updates/`:

- File naming: `YYYY-MM-DD-descriptive-slug.md`.
- Use the template: `docs/updates/_TEMPLATE.md`.
- Add to the index: `docs/updates/index.md` (newest first).
- Optionally add a short entry to `CHANGELOG.md` linking to the update.
- See guidance: `docs/updates/README.md`.

These updates complement the CHANGELOG and should not duplicate full release notes.

### 2.3. SHOULD: Update the Right Page for the Right Change

- New/changed MCP tools → `docs/reference/tools.md` (parameters, returns, examples).
    - Cross-link to concepts (e.g., canonical events, categories) when relevant.
- New/changed core concepts → `docs/concepts/` (e.g., `canonical-events.md`, `categories.md`).
    - Avoid API details here; link to `reference/tools.md`.
- Architecture/service design changes → `docs/architecture/implementation.md`.
- Operational/logging/health guidance → `docs/developer/logging-and-health.md`.
- Best-practices for tool descriptions → `docs/developer/best-practices.md`.
- ActivityWatch compatibility matrix → `docs/reference/activitywatch-integration.md`.

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

-   [ ] If code behavior or APIs changed, updated `docs/reference/tools.md` (and added examples).
-   [ ] If new concept or major change, updated/added under `docs/concepts/` and linked from relevant pages.
-   [ ] If architecture changed, updated `docs/architecture/implementation.md`.
-   [ ] If operational behavior/logging changed, updated `docs/developer/logging-and-health.md`.
-   [ ] If work was task-scoped (feature/bug/refactor), added an entry in `docs/updates/` and `docs/updates/index.md`.
-   [ ] Updated `docs/index.md` if navigation/structure changed.
-   [ ] Removed duplication and updated cross-links; added "Last updated" where applicable.
-   [ ] Root `README.md` links to `docs/index.md` remain valid.

### 2.8. Formatting & Style

- Markdown only. Prefer bullets and short paragraphs.
- Include examples and exact parameter names/types where helpful.
- Use code fences with languages for commands and snippets.
- Use PlantUML in Markdown for diagrams when appropriate.
- Provide docstrings for public APIs in code (PEP 257 style) with type hints.

### 2.9. SDLC/SRS (if applicable)

- Maintain SRS under `docs/SDLC/SRS/` when the project requires formal specs (not typical for this repo).

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
- `docs/updates/README.md`
- `docs/updates/index.md`
- `CHANGELOG.md`