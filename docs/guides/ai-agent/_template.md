---
type:        "{{type_value}}" # Use "agent_requested" or "always_apply"
name:        "{{name}}"
priority:    {{priority_value}} # Higher number = higher priority
scope:       "{{scope_value}}" # e.g., "git-*", "tests/**", ".*"
description: "{{description}}"
cross_reference: [{{cross_references}}] # List of other rule filenames
apply_when:   "{{apply_when_predicate}}" # e.g., "task_creates_commits == true", "always"
---

# AI Agent Rule/Guide: {{name}}

- **Type**: {{type_value}}
- **Priority**: {{priority_value}}
- **Scope**: {{scope_value}}
- **Description**: {{description}}
- **Cross-Reference**: {{cross_references}}
- **Apply When**: {{apply_when_predicate}}

## 1. Purpose

[Explain the purpose of this rule or guide. What problem does it solve or what behavior does it define for the AI agent?]

## 2. Rule/Guideline Details

[Provide the specific instructions, conventions, or guidelines that the AI agent should follow. Use clear, concise language. Include examples where necessary.]

### Sub-section Example

[Further breakdown of the rule if needed.]

## 3. Examples

```
# Example code snippet, command, or interaction demonstrating the rule in practice.
```

## 4. Rationale / Justification

[Explain why this rule is important or the reasoning behind its design. What are the benefits of following this rule?]

## 5. Related Information

[Link to any other relevant documentation, such as architectural decisions, implementation guides, or external standards.]

# References

- [Link to additional resources, specifications, or related tickets.]
