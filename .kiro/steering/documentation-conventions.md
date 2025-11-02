---
inclusion: fileMatch
fileMatchPattern: 'docs/**'
---

# Documentation Conventions

**Priority**: 20  
**Scope**: docs/**  
**Description**: Standardized documentation format and policy for all projects.

## Documentation Structure

All documentation MUST live under `docs/` and follow the established structure:

```
docs/
├── index.md                      # Landing page (keep updated)
├── getting-started/quickstart.md # Setup in 5 minutes
├── concepts/                     # Core ideas
├── reference/                    # Source of truth for APIs/specs
├── architecture/implementation.md# Technical details & design
├── developer/                    # Contributor/ops docs
├── updates/                      # "What Was Implemented" docs
│   ├── README.md
│   ├── _TEMPLATE.md
│   └── index.md
└── archive/                      # Historical docs only
```

- Do NOT add documentation files outside `docs/`.

## Implementation Notes

Task-scoped implementation notes (often written by agents) MUST be placed in `docs/updates/`:

- File naming: `YYYY-MM-DD-descriptive-slug.md`.
- Use the template: `docs/updates/_TEMPLATE.md`.
- Add to the index: `docs/updates/index.md` (newest first).
- Optionally add a short entry to `CHANGELOG.md` linking to the update.
- See guidance: `docs/updates/README.md`.

## Content Guidelines

- **Update the Right Page for the Right Change**:
  - New/changed tools → `docs/reference/` (parameters, returns, examples)
  - New/changed core concepts → `docs/concepts/`
  - Architecture/service design changes → `docs/architecture/implementation.md`
  - Operational guidance → `docs/developer/`

- **MUST NOT Duplicate Content**: One home per concept. Reference, don't repeat.

- **Maintain Cross-Links and Freshness**: When moving/renaming docs, update internal links in affected files.

## Formatting & Style

- Markdown only. Prefer bullets and short paragraphs.
- Include examples and exact parameter names/types where helpful.
- Use code fences with languages for commands and snippets.
- Use PlantUML in Markdown for diagrams when appropriate.
- Provide docstrings for public APIs in code with type hints.

## PR Checklist

When making changes that affect documentation:

-   [ ] If code behavior or APIs changed, updated relevant reference docs
-   [ ] If new concept or major change, updated/added under `docs/concepts/` and linked from relevant pages
-   [ ] If architecture changed, updated `docs/architecture/implementation.md`
-   [ ] If work was task-scoped, added an entry in `docs/updates/` and `docs/updates/index.md`
-   [ ] Updated `docs/index.md` if navigation/structure changed
-   [ ] Removed duplication and updated cross-links; added "Last updated" where applicable