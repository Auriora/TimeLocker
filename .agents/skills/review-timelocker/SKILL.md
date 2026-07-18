---
name: review-timelocker
description: Review TimeLocker code and documentation through project stewardship, Restic backup and recovery, Python CLI architecture, security and privacy, reliability and testing, operations and portability, and documentation lifecycle perspectives. Use for whole-repository health reviews, pull request or diff reviews, architecture audits, security reviews, test-quality reviews, documentation audits, release-readiness reviews, or focused reviews of TimeLocker modules and durable docs. Produce evidence-backed, deduplicated findings and remain read-only unless the user separately authorizes remediation.
---

# Review TimeLocker

Perform a findings-first review grounded in TimeLocker's own authority and
implementation. Optimize for defects, recovery risk, contract drift, security
exposure, operational failure, and documentation disagreement rather than style
preferences.

## Load The Review Contract

Read these references completely before reviewing:

- [expert-panel.md](references/expert-panel.md) for role responsibilities and
  evidence priorities.
- [review-contract.md](references/review-contract.md) for severity, confidence,
  finding fields, synthesis, and report format.

## 1. Classify The Request

Classify the requested scope as one or more of:

- whole repository;
- pull request, commit, branch, or diff;
- focused code or subsystem;
- documentation or specification;
- security and privacy;
- tests and reliability; or
- release or closure readiness.

Treat `review`, `audit`, `assess`, `inspect`, and `report findings` as read-only.
Do not edit files, change spec task state, create durable reports, commit, or
contact external services unless the user explicitly requests the corresponding
action. A request to address findings is a new implementation task governed by
repository planning and approval rules.

## 2. Establish Authority And Freshness

Read the smallest complete authoritative set for the scope:

1. root `AGENTS.md` and any deeper instruction file;
2. `CHARTER.md` for mandate, boundaries, and governance;
3. matching rules under `docs/guides/ai-agent/`;
4. Git status and the requested diff or current tree;
5. active specs when the scope implements, validates, or closes spec work;
6. relevant durable requirements, architecture, implementation, testing,
   process, and reference docs; and
7. the code, tests, configuration, workflows, and generated contracts that own
   implemented behavior.

Prefer Agent Workbench for orientation, targeted navigation, impact, docs
discovery, diagnostics, and validation planning. Use Spec Lifecycle Manager for
authoritative spec readiness, traceability, evidence, promotion, and closure.
Treat planned validation and advisory tool output as guidance, not executed proof.

When sources disagree, use the authority order in `CHARTER.md`. Report material
drift as a finding; do not silently choose planned prose over implementation.

## 3. Declare A Scope Receipt

Before findings, record:

- requested review mode and revision or diff examined;
- included paths and explicitly excluded areas;
- authorities and evidence sources consulted;
- checks actually executed and their result;
- unavailable or skipped evidence; and
- whether the result is complete, bounded, or partial.

Do not claim whole-repository coverage from a sampled or truncated review.

## 4. Gather Evidence

Trace each suspected issue across the smallest useful evidence chain:

```text
charter or requirement -> design or contract -> implementation -> tests/config
                         -> durable documentation or operational guidance
```

Use exact repo-relative paths, line numbers, symbols, configuration keys,
commands, or reproducible behavior. Read enough surrounding context to rule out
local false positives. Inspect callers and tests before claiming an interface or
behavior is unused, unsafe, incompatible, or uncovered.

Never expose repository passwords, credentials, tokens, callback codes, secret
arguments, or sensitive path contents. Describe safe evidence categories instead.

## 5. Apply The Expert Panel

Apply all seven roles to whole-repository reviews. For focused reviews, apply
every materially relevant role and list any role omitted as not applicable.
Roles are review lenses, not a requirement to manufacture seven findings.

For each role:

1. follow its remit and priority questions;
2. record candidate observations with supporting evidence;
3. distinguish confirmed defects from risks, drift, and notes; and
4. hand overlapping observations to synthesis rather than assigning duplicate IDs.

Multi-agent execution is optional. Use it only when user, platform, and
repository instructions authorize delegation. The entire workflow must remain
usable by one agent.

## 6. Validate Candidate Findings

Before confirming a finding:

- reproduce or triangulate the behavior where safe;
- check nearby tests, configuration, callers, and documented exceptions;
- distinguish a failed executed command from a planned command;
- state when evidence is static rather than runtime-derived;
- lower confidence when scope, environment, or tooling is incomplete; and
- avoid security, data-loss, or recovery claims that the evidence cannot support.

Do not downgrade a serious issue merely because remediation is difficult.
Do not elevate speculative concerns merely because their theoretical impact is high.

## 7. Synthesize And Prioritize

Group observations by underlying cause. Emit one finding when multiple roles
identify the same defect, and list every contributing role. Preserve existing
`TLR-###` identifiers when extending the same review; append new identifiers
without renumbering.

Order findings by severity, then confidence and blast radius. Keep optional
improvements out of the blocking findings list unless they address a concrete
maintainability or operational consequence.

## 8. Report Findings First

Use the report structure in [review-contract.md](references/review-contract.md).
Lead with actionable findings. Follow with open questions or assumptions, the
scope receipt, and a short panel summary.

If there are no actionable findings, say so explicitly and still report the
scope, checks, limitations, and residual risks. Never imply that a clean review
proves the absence of defects.

## 9. Route Follow-Up

Recommend one primary destination for each finding:

- direct fix for a narrow approved correction;
- active spec task when already in accepted scope;
- new spec for cross-cutting, behavioral, migration, or governance work;
- GitHub issue for unapproved, assigned, or insufficiently specified work; or
- durable documentation correction when current accepted behavior is merely stale.

Do not implement the remedy during a review-only request. When remediation is
authorized, re-enter TimeLocker's planning, lifecycle, approval, validation,
promotion, and closure workflow.
