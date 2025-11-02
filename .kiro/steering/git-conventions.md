---
inclusion: always
---

# Git Commit & Branching Conventions

**Priority**: 15  
**Scope**: git-*  
**Description**: Standardized commit message format and policy for all projects.

## Git Commit Message Format

Always use this standardized format for commit messages:

```
<type>(optional scope): <subject-description>

<description>

<Tags and External References>
```

### Commit Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools and libraries such as documentation generation

### Format Rules

- **Type**: Required, lowercase, from the approved list above
- **Scope**: Optional, in parentheses, describes the area of change (e.g., `config`, `cli`, `backup`)
- **Subject**: Required, concise, imperative mood, no period at end, ≤ 72 characters
- **Body Wrapping**: Wrap the description/body at roughly 72 characters per line for readability
- **Description**: Required, detailed explanation of what and why, can be multiple paragraphs
- **Tags/References**: Optional, include issue numbers, external references, breaking changes; prefer linking issues using phrases like "Refs #123" or "Fixes #123"

### Example

```
refactor(config): remove deprecated configuration options

Remove legacy configuration options that were deprecated in v1.0.0.
This simplifies the configuration schema and reduces maintenance overhead.

Fixes #456
```

## Git Policy

- Commits should always be done in logical groups of changes if multiple different types of changes are made
- All changes should be done on a branch - not on the top of tree. A branch should be created for the change before changing or committing changes
- Branch naming: use descriptive prefixes, e.g., `feature/<short-desc>`, `fix/<issue-#>`, `docs/<topic>`, `chore/<task>`
- When applicable, link issues in commit messages and PR descriptions using "Refs #<id>" for references and "Fixes #<id>" or "Closes #<id>" for auto-closing