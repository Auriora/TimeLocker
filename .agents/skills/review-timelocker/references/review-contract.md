# TimeLocker Review Contract

## Classification

Classify each item as one of:

- **confirmed defect:** evidence demonstrates incorrect implemented behavior;
- **documentation drift:** durable prose disagrees with accepted implementation;
- **risk:** a credible failure mode exists but has not been demonstrated;
- **unverified concern:** evidence is incomplete or a required check could not run; or
- **note:** non-actionable context that helps interpret the review.

Only confirmed defects, documentation drift, and actionable risks belong in the
findings list. Keep notes in the panel summary.

## Severity

| Level | Use when |
|-------|----------|
| `critical` | Likely or demonstrated unrecoverable data loss, credential compromise, arbitrary code execution, or a release-blocking systemic failure. |
| `high` | Material backup/restore failure, public-contract break, serious security weakness, or broad operational outage. |
| `medium` | Bounded correctness, reliability, maintainability, test, or documentation defect with a realistic user or contributor consequence. |
| `low` | Localized issue with limited impact but a concrete cost or failure mode. |

Do not use severity to encode confidence. A high-impact theory with incomplete
evidence remains an unverified concern with explicit potential impact.

## Confidence

- `high`: reproduced or supported by multiple authoritative evidence sources.
- `medium`: direct static evidence exists, but runtime or environment proof is absent.
- `low`: plausible and relevant, but scope or evidence is materially incomplete.

## Finding Record

Use this schema for every finding:

```markdown
### TLR-001 — Short actionable title

- Severity: high | medium | low | critical
- Confidence: high | medium | low
- Classification: confirmed defect | documentation drift | risk | unverified concern
- Expert roles: role names
- Evidence: `path:line`, symbol, configuration, or executed command result
- Consequence: concrete user, recovery, security, operational, or maintenance impact
- Remedy: smallest safe correction or decision
- Validation: check that would prove the remedy
- Routing: direct fix | active Spec NNN task | new spec | GitHub issue | durable-doc correction
```

Keep evidence concise but reproducible. Cite the primary source closest to the
defect and add supporting sources only when they change confidence.

## Deduplication

Treat observations as one finding when they share the same underlying cause and
remedy. Merge role attribution, choose severity from the largest demonstrated
impact, and choose confidence from the combined evidence. Do not merge separate
causes merely because they affect the same command or document.

Within one continuing review, retain existing IDs and append new IDs. If a
finding changes materially, record its updated status instead of reusing the ID
for a different issue.

## Report Structure

```markdown
## Findings

[Findings ordered by severity, confidence, and blast radius.]

## Open Questions And Assumptions

[Only questions that affect interpretation or remediation.]

## Scope Receipt

- Mode:
- Revision or diff:
- Included:
- Excluded:
- Authorities and evidence:
- Checks executed:
- Skipped or unavailable:
- Coverage: complete | bounded | partial

## Panel Summary

[One concise paragraph naming roles applied, clean areas, and residual risk.]
```

For a clean review, write `No actionable findings.` under Findings, then provide
the same scope receipt and limitations. Never describe a bounded clean review as
proof that the repository contains no defects.
