---
id: timelocker-project-charter
title: TimeLocker project charter
doc_type: governance
status: active
owner: Auriora Team
audience:
  - users
  - contributors
  - maintainers
  - ai-developers
last_reviewed: 2026-08-12
source_of_truth: true
---

# TimeLocker Project Charter

## Purpose

This charter is the enduring authority for TimeLocker's mandate, project
boundaries, operating principles, governance, and measures of success. It helps
users, contributors, maintainers, and coding agents decide whether proposed work
belongs in TimeLocker and how material decisions are made.

Delivery specifications may define an approved change, but they remain
subordinate to this charter and disappear after their accepted content is
promoted. The charter does not replace code, tests, product documentation, or
the issue tracker in the areas those sources own.

## Mandate

TimeLocker makes reliable backup and recovery workflows easier to configure,
operate, automate, and understand. It provides a CLI-first, Python-based layer
over Restic for managing repositories, backups, snapshots, restores,
credentials, selection rules, policies, schedules, monitoring, and related
integrations.

The project exists to reduce the operational complexity and inconsistency that
otherwise accumulates around raw backup commands. It should provide safer
defaults, stable workflows, clear errors, reusable orchestration, and enough
observability for an operator to understand what happened and recover when
something goes wrong.

## Who TimeLocker Serves

- Operators and system administrators who need repeatable backup and recovery
  workflows across local and supported cloud storage.
- Individuals and teams who want safer configuration, credential handling,
  selection, scheduling, monitoring, and restore operations around Restic.
- Developers who need to automate or integrate the same supported backup
  workflows without maintaining another independent orchestration path.
- Contributors and maintainers who need clear product boundaries and stable
  contracts for evolving the project safely.

## Operating Principles

1. **Recovery is the outcome.** A backup feature is valuable only when its data
   can be found, understood, and restored. Recovery correctness takes priority
   over feature volume.
2. **Safety before convenience.** Protect credentials, avoid destructive
   surprises, validate risky inputs, and make dry-run or confirmation paths
   available where practical.
3. **One supported path per responsibility.** Shared resolution,
   configuration, credentials, monitoring, and command behavior should have
   clear owners instead of drifting duplicate implementations.
4. **Stable automation contracts.** Preserve documented commands, exit
   behavior, configuration, and supported Python entry points unless an
   explicitly reviewed change includes compatibility and migration treatment.
5. **Observable and explainable operation.** Errors and progress should help an
   operator identify the affected repository, operation, and safe next action
   without exposing secrets.
6. **Evidence over assertion.** Tests, executable checks, code-derived
   contracts, and reproducible validation support acceptance decisions.
7. **Current documentation over visible history.** Durable docs describe the
   accepted state; Git and lifecycle history preserve completed delivery
   context.
8. **Zero idle residency.** TimeLocker must not require a continuously resident
   daemon or privileged background process. Scheduled and explicit work should
   use bounded, short-lived processes that exit when the operation or request
   completes. Optional user-session presentation may remain open only by
   explicit operator choice and must not require a resident privileged backend.

## Current Scope

TimeLocker's mandate includes:

- a supported command-line interface for repository, backup, snapshot,
  restore, selection, credential, policy, scheduling, monitoring, and
  integration workflows;
- reusable Python services that implement or support the same product
  workflows rather than creating a separate competing product surface;
- Restic repository orchestration for local, S3-compatible, and Backblaze B2
  storage supported by the project;
- filesystem-based configuration, secure credential resolution, validation,
  logging, progress reporting, and operational diagnostics;
- automation and optional desktop notification or system-tray integration that
  complements the CLI;
- documentation, tests, release practices, and compatibility controls needed
  to operate and evolve those capabilities safely.

Scope inclusion requires a clear connection to dependable backup or recovery
operation, a named ownership boundary, testable acceptance criteria, and a
maintenance path consistent with the project principles.

## What TimeLocker Is Not

TimeLocker is not:

- a replacement backup engine or repository format for Restic;
- a hosted backup service, storage provider, or centralized control plane;
- an implemented REST API or database-backed application server;
- a full desktop GUI or mobile application; optional system-tray integration
  is a companion to the CLI, not a separate product;
- a general-purpose cloud-storage SDK or secrets vault;
- a guarantee of disaster recovery without operator-owned repository access,
  retention choices, restore testing, and infrastructure readiness;
- a place to add speculative product surfaces directly to current-state
  architecture or reference documentation.

Work outside the current mandate requires an explicit project-scope decision
before it becomes active delivery work. Approval of an investigation or
proposal does not by itself amend this charter.

## Responsibility Boundaries

### TimeLocker owns

- its CLI and documented reusable Python contracts;
- orchestration, validation, configuration, credential-resolution interfaces,
  and operator-facing behavior implemented in this repository;
- compatibility decisions for TimeLocker commands, configuration, and public
  package entry points;
- project documentation, tests, release artifacts, and supported integration
  seams.

### Restic owns

- the underlying backup engine, repository format, snapshot semantics, and raw
  command capabilities;
- upstream behavior that TimeLocker invokes but does not redefine.

### Operators and integrating applications own

- storage accounts, infrastructure, access policy, network availability,
  retention intent, and recovery objectives;
- secure deployment of credentials and environment configuration;
- validation that backups and restores meet their operational and compliance
  needs;
- application-specific workflow, state, and user experience outside the
  supported TimeLocker contracts.

## Governance And Decision Rights

The **Auriora Team** owns this charter and the enduring project direction. A
**project steward** is the role responsible for interpreting the charter,
confirming decision routing, and ensuring material changes receive the required
review. Maintainers own decisions within an approved scope; contributors
provide proposals and evidence through the normal review process.

Decision handling follows these rules:

- Routine fixes and compatible improvements may proceed through the normal
  issue, review, validation, and commit workflow when they clearly fit this
  charter.
- Non-trivial delivery work uses an approved lifecycle specification with
  explicit requirements, design, tasks, evidence, durable promotion, and
  closure.
- Changes to the mandate, explicit exclusions, responsibility boundaries,
  security posture, public contracts, or compatibility policy require explicit
  Auriora Team approval.
- Public CLI, configuration, or supported Python contract changes require
  caller and impact analysis, compatibility treatment, tests, documentation,
  and release/versioning review.
- Security- or data-sensitive changes require review proportionate to their
  access, disclosure, corruption, and recovery risk.
- Unapproved or insufficiently defined work remains in GitHub or a proposal;
  it must not be presented as accepted current behavior.

## Measures Of Success

TimeLocker is succeeding when the following signals remain healthy and improve
over time:

- **Recovery confidence:** supported backup, snapshot, and restore workflows
  pass their acceptance and regression checks, and recovery guidance is current.
- **Operational safety:** credentials are not exposed, destructive actions are
  bounded, failures identify safe next actions, and security-sensitive changes
  receive explicit review.
- **Contract stability:** documented CLI discovery and supported automation
  paths remain compatible, or changes provide reviewed migration evidence.
- **Product usability:** installation, repository setup, backup, inspection,
  and restore paths are documented and can be followed without hidden project
  knowledge.
- **Quality:** required CI checks pass, repository coverage meets the configured
  threshold, and risk-appropriate focused tests accompany changes.
- **Maintainability:** each important responsibility has a clear implementation
  owner, duplicate paths decrease, and temporary delivery specs close after
  durable promotion.

These are health measures, not promises of a particular feature, release date,
service level, or adoption target. Quantitative thresholds belong in the
configuration, test policy, release process, or an approved delivery spec that
can keep them current.

## Sources Of Authority

Use the following order to answer project questions:

1. This charter owns enduring mandate, boundaries, principles, governance, and
   success measures.
2. Code, tests, configuration, and generated contracts own implemented
   behavior where prose and execution disagree.
3. Durable documentation under `docs/` owns accepted current requirements,
   architecture, procedures, and references.
4. Active packages under `docs/specs/` own approved temporary delivery scope,
   sequencing, acceptance criteria, and evidence.
5. GitHub owns assignment, issue state, and proposed work that is not yet an
   active delivery contract.
6. Git history and compact lifecycle records preserve completed delivery
   evidence; they are not current product authority.

## Change Rules

Review this charter whenever a proposal changes the project mandate, supported
product surface, responsibility boundaries, governance, or success definition.
A charter amendment must:

- state the problem and the durable principle or boundary being changed;
- identify affected users, public contracts, documentation, and active specs;
- receive explicit Auriora Team approval;
- update repository entry points without duplicating the charter;
- include appropriate validation and a recoverable Git record.

Editorial clarification may use a direct documentation change when it does not
alter meaning. Material amendments require a temporary governance spec and must
be promoted here before that package closes.

## What To Do Next

- **Use TimeLocker:** start with the [README](./README.md) and
  [installation guide](./docs/guides/user/installation.md).
- **Understand current behavior:** use the
  [documentation hub](./docs/README.md) and its user, architecture,
  implementation, testing, and reference paths.
- **Contribute:** read [CONTRIBUTING.md](./CONTRIBUTING.md), then check GitHub
  for issue ownership and the [active-spec index](./docs/specs/README.md) for
  approved delivery work.
- **Work as an agent:** start with [AGENTS.md](./AGENTS.md) and the centralized
  agent rules it identifies; use this charter for project-fit decisions.
- **Propose work outside the current scope:** open or refine a GitHub proposal
  and obtain an explicit scope decision before creating implementation tasks.
