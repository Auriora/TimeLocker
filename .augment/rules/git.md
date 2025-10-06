---
type: "agent_requested"
description: "Example description"
---

# Git

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
- **Scope**: Optional, in parentheses, describes the area of change (e.g., `mdns`, `traefik`, `monitoring`)
- **Subject**: Required, concise description in imperative mood, no period at end
- **Description**: Required, detailed explanation of what and why, can be multiple paragraphs
- **Tags/References**: Optional, include issue numbers, external references, breaking changes

### Example

refactor(mdns): remove avahi-daemon container from mDNS automation

## Git Policy

- commits should always be done in logical groups of changes if multiple different types of changes are made
- all changes should be done on a branch - not on the top of tree. a branch should be created for the change before changing or commtting changes