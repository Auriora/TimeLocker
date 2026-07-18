# TimeLocker Expert Panel

Use these roles as complementary evidence lenses. Attribute a synthesized
finding to every role that materially supports it.

## 1. Project Steward And Operator Advocate

**Remit:** Charter fit, user value, scope, public behavior, compatibility, and
operator comprehension.

**Prioritize:**

- backup and recovery outcomes over feature volume;
- safe, comprehensible CLI workflows and failure messages;
- explicit responsibility boundaries between TimeLocker, Restic, and operators;
- compatibility of documented CLI, configuration, and Python contracts; and
- proposed surfaces that exceed the approved mandate.

**Evidence:** `CHARTER.md`, durable requirements, CLI help and contracts,
configuration references, user guides, changelog, and implementation behavior.

## 2. Restic And Backup/Recovery Specialist

**Remit:** Correct orchestration of repositories, backups, snapshots, restores,
selection, retention, and supported storage backends.

**Prioritize:**

- false-success, incomplete backup, data-loss, and unrecoverable-restore paths;
- preservation of Restic repository and snapshot semantics;
- repository identity, backend URI, password, and command construction;
- include/exclude selection and retention behavior; and
- validation that recovery—not merely backup creation—is possible and explained.

**Evidence:** Restic adapters and command builders, repository services,
backup/restore flows, subprocess handling, focused tests, and recovery guidance.
Do not assume upstream Restic behavior when local evidence or official upstream
contracts must be checked.

## 3. Python CLI Architect

**Remit:** Python package integrity, Typer CLI contracts, boundaries, dependency
direction, error translation, and maintainability.

**Prioritize:**

- separation of CLI orchestration, services/domain behavior, adapters,
  configuration, and monitoring integrations;
- duplicate service seams or service-locator paths;
- public command, option, exit, and supported Python compatibility;
- exception specificity, chaining, ownership, and user-facing translation;
- global mutable state, import cycles, hidden coupling, and unnecessary abstraction; and
- dependency and Python-version agreement with `pyproject.toml`.

**Evidence:** `src/TimeLocker/`, entry points, callers, imports, public tests,
architecture docs, and package configuration.

## 4. Security And Privacy Reviewer

**Remit:** Credentials, repository access, command execution, filesystem safety,
logging, destructive operations, and privacy.

**Prioritize:**

- secrets in arguments, logs, errors, fixtures, docs, environment handling, or Git;
- shell injection, unsafe subprocess construction, path traversal, and symlink risks;
- credential precedence, storage, lifetime, disclosure, and least privilege;
- destructive actions without validation, confirmation, dry run, or bounded targets;
- insecure defaults, permission handling, audit gaps, and sensitive metadata; and
- claims that confuse Restic encryption with complete operational security.

**Evidence:** security services, credential resolvers, subprocess boundaries,
logging and telemetry, filesystem code, configuration, security tests, and
security architecture. Report secret categories, never secret values.

## 5. Reliability And Test Strategist

**Remit:** Behavioral assurance, regression protection, failure modes, test
isolation, and meaningful quality gates.

**Prioritize:**

- backup, restore, repository, selection, and credential failure paths;
- tests that assert implementation details instead of public behavior;
- mock-heavy tests that cannot reveal integration defects;
- platform, network, timing, filesystem, and concurrency isolation;
- marker, timeout, coverage, and discovery agreement with `pyproject.toml`;
- untested correctness properties and compatibility seams; and
- skipped, flaky, or falsely passing checks.

**Evidence:** changed code and matching tests, `tests/`, test documentation,
pytest configuration, CI workflows, and executed results. Coverage percentage
alone is not proof of behavioral adequacy.

## 6. Operations And Portability Reviewer

**Remit:** Scheduling, monitoring, diagnostics, platform behavior, supported
storage, failure recovery, and day-two operation.

**Prioritize:**

- observable operation with repository and action context but no secrets;
- retry, timeout, cancellation, partial failure, and interrupted-operation behavior;
- Linux, macOS, Windows, XDG, path, permission, and process differences;
- scheduler and notification lifecycle, idempotency, and cleanup;
- local, S3-compatible, and Backblaze B2 configuration and diagnostics; and
- actionable runbooks for verifying backups and performing restores.

**Evidence:** scheduling and monitoring services, integrations, filesystem paths,
backend adapters, operational tests, user guides, and process documentation.

## 7. Documentation And Lifecycle Reviewer

**Remit:** Current-state accuracy, source authority, discoverability, active-spec
integrity, traceability, and removal of delivery-history clutter.

**Prioritize:**

- disagreement among code, tests, config, durable docs, and active specs;
- future-only behavior presented as implemented;
- duplicated concepts, broken links, orphaned identifiers, and stale commands;
- historical plans, reports, updates, or closed specs left in current docs;
- missing promotion, evidence, closure, or follow-up routing; and
- front doors that fail to guide users and agents to the right authority.

**Evidence:** `README.md`, `CHARTER.md`, `AGENTS.md`, `docs/`, active lifecycle
packages, link and Markdown checks, Git history, and implemented contracts.
