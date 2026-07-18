---
title: Documentation resources
doc_type: reference
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Documentation Resources

This directory is the canonical location for non-prose assets consumed by
TimeLocker documentation and documentation-generation scripts.

- `images/` contains rendered diagrams and their editable source where useful.
- `restic_commands.json` contains Restic man-page data used by
  `scripts/json2command_definition/json2command_definition.py`.

Product logos and application branding remain in the repository-root
`resources/` directory. Do not recreate hidden `.resources/` or place generated
source data directly at the root of `docs/`.
