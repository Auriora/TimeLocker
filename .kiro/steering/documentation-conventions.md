---
inclusion: fileMatch
fileMatchPattern: 'docs/**'
---

# Documentation Conventions

**Priority**: 20  
**Scope**: docs/**  
**Description**: Standardized documentation format and policy for all projects.

## Documentation Structure

All documentation MUST live under `docs/` and follow the established structure.

### Source Folder Documentation Policy

**IMPORTANT**: The `src/` folder structure is for code only. Documentation files should NOT be placed in `src/` with the following exception:

- **Allowed**: Minimal `README.md` files in source folders that:
  - Briefly explain the folder's purpose (1-3 sentences)
  - Point to the relevant detailed documentation in `docs/`
  - Provide a quick structural overview if helpful
  
- **NOT Allowed**: 
  - Detailed documentation, usage guides, or examples in `src/`
  - Architecture explanations, design decisions, or implementation details in `src/`
  - Any documentation that duplicates content from `docs/`

**Example of acceptable `src/` README.md**:
```markdown
# Module Name

Brief one-line description of what this module does.

For detailed documentation, see [docs/3-implementation/module-name.md](../../../docs/3-implementation/module-name.md).
```

All comprehensive documentation MUST be placed in the appropriate `docs/` subfolder:

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
- **IMPORTANT**: Architecture documentation MUST go in `docs/2-architecture/`, NOT `docs/architecture/`.
- **IMPORTANT**: Task and project tracking documents MUST go in `docs/0-project-management/`, NOT `docs/tasks/`.

## Implementation Notes and Reports

### Updates (Implementation Logs)

Task-scoped implementation notes (often written by agents) MUST be placed in `docs/updates/`:

- File naming: `YYYY-MM-DD-HHMMSS-descriptive-slug.md` (include timestamp for uniqueness).
- Use the template: `docs/updates/_template.md`.
- Add to the index: `docs/updates/index.md` (newest first).
- Optionally add a short entry to `CHANGELOG.md` linking to the update.
- See guidance: `docs/updates/README.md`.

### Reports (Status and Analysis)

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

## Content Guidelines

- **Update the Right Page for the Right Change**:
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
  - Traceability matrices → `docs/traceability/`
  - Historical documentation → `docs/archive/`

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

-   [ ] If code behavior or APIs changed, updated relevant reference docs in `docs/reference/`
-   [ ] If requirements changed, updated `docs/1-requirements/`
-   [ ] If architecture changed, updated `docs/2-architecture/`
-   [ ] If implementation details changed, updated `docs/3-implementation/`
-   [ ] If testing approach changed, updated `docs/4-testing/`
-   [ ] If work was task-scoped, added an entry in `docs/updates/` with timestamp and updated `docs/updates/index.md`
-   [ ] If creating a status report, added to `docs/reports/` with timestamp
-   [ ] Updated `docs/README.md` if navigation/structure changed
-   [ ] Removed duplication and updated cross-links; added "Last updated" where applicable