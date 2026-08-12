---
title: Protected system deployment requirements
doc_type: spec
artifact_type: requirements
status: implemented
owner: Auriora Team
last_reviewed: 2026-08-12
---

# Requirements

## Introduction

TimeLocker has validated primitives for immutable releases, packaged system
assets, compatibility probes, atomic selection, and rollback. It does not have
one supported administrator workflow that prepares an artifact and manifest,
stages trusted inputs, performs the transaction, reports evidence, and offers a
repeatable rollback.

Spec 010 therefore used a repository-owned T011 acceptance harness plus
manually supplied commit IDs, hashes, manifests, and temporary artifact paths.
That harness successfully activated the accepted Linux Mint release, but it is
not an appropriate long-term installation or upgrade interface. Live operation
also showed that its continuously resident privileged backend can enter a
read-notify-read feedback loop and consume CPU while no backup or retention
operation is running. A resident TimeLocker daemon is therefore rejected as an
architectural requirement, not merely scheduled for performance tuning.

## Goals

- Provide one supported administrator entrypoint for protected installation,
  upgrade, inspection, and rollback.
- Derive and verify artifact identity, release metadata, hashes, and staging
  paths without requiring operators to assemble them manually.
- Preserve the proven preflight-first, fail-closed, rollback-safe transaction.
- Use trusted, root-owned staging and evidence locations with bounded cleanup.
- Keep release publication, protected host deployment, and backup or retention
  execution as distinct approval boundaries.
- Preserve a portable deployment model while delivering and accepting Linux
  systemd behavior first.
- Replace the resident privileged backend with bounded one-shot helpers and
  sanitized atomically written status state.

## Non-Goals

- Publishing TimeLocker to PyPI or automatically creating a GitHub release.
- An unattended update daemon, silent automatic upgrades, or remote fleet
  management.
- A continuously resident TimeLocker-owned privileged control daemon, event
  broker, heartbeat process, or status service.
- Changing backup, restore, selection-set, retention-policy, or repository
  credential semantics.
- Triggering backup or retention as a side effect of deployment.
- A general-purpose package manager or replacement for operating-system
  packaging.
- Removing protected configuration, credentials, schedules, or durable run
  records during rollback.
- Claiming a live Windows deployment before its platform implementation and
  acceptance are separately evidenced.

## Glossary

| Term | Definition |
|------|------------|
| Deployment entrypoint | The supported administrator command or executable that owns protected install, upgrade, status, and rollback orchestration. |
| Release artifact | A validated TimeLocker wheel or an approved published release containing the wheel and its integrity metadata. |
| Deployment transaction | The bounded sequence of input validation, private staging, candidate installation, preflight, activation, verification, evidence capture, and recovery. |
| Staging root | A trusted root-owned location used internally by the deployment entrypoint; it is not an operator-authored temporary script or manifest location. |
| Selected release | The immutable release referenced by `/opt/timelocker/selected-release.json` and resolved by stable system launchers. |
| Deployment evidence | Redacted, root-owned records sufficient to determine inputs, gates, outcome, rollback state, and residual action without exposing credentials. |

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `CHARTER.md` | TimeLocker is CLI-first and prioritizes dependable backup and recovery operation. | high | Governing mandate. |
| `docs/1-requirements/system-operations.md` | Installation, upgrade, service changes, activation, and rollback are root-only; releases are immutable and fail closed. | high | Extend with supported deployment UX. |
| `docs/2-architecture/system-architecture.md` | Stable launchers resolve one protected selected release independently of user environment. | high | Preserve trust boundary. |
| `docs/guides/user/installation.md` | The repository currently exposes primitives but no general protected installer command. | high | This spec closes that documented gap. |
| `docs/processes/version-management.md` | Publication and protected host activation are separate, approval-gated transactions. | high | Do not collapse the boundaries. |
| `src/TimeLocker/system_control/deployment.py` and release launcher modules | Asset validation, compatibility probes, immutable selection, and rollback primitives exist. | high | Design should reuse or consolidate these contracts. |
| `scripts/deploy_t011_linux.py` and its tests | Spec 010 proved a preflight-first transaction and exposed risks from temporary scripts, renamed wheels, and manual inputs. | high | Acceptance harness is input, not the final public interface. |
| Linux Mint live deployment of commit `a67c83ac09ac29b94a3ed481ee536b3380db3337` | Candidate selection, previous-release preservation, services, sockets, timers, CLI, and tray status succeeded. | high | Runtime evidence from 2026-07-28. |

## Durable Impact

| Durable area | Action | Target | Notes |
|--------------|--------|--------|-------|
| requirements | modify | `docs/1-requirements/system-operations.md` | Add supported deployment lifecycle and evidence requirements. |
| architecture | modify | `docs/2-architecture/system-architecture.md` | Add deployment entrypoint, staging, transaction, and platform boundary. |
| process | modify | `docs/processes/version-management.md` | Define artifact-to-host activation procedure. |
| runbook | add or modify | `docs/guides/user/installation.md` and deployment runbook | Replace manual assembly with supported commands. |
| command reference | modify | `docs/reference/timelocker-cli-command-hierarchy.md` | Document administrator-only deployment surface. |
| testing | clarify | `docs/4-testing/` if reusable deployment validation is added | Separate simulated, installed-artifact, and live acceptance evidence. |

## Staged Readiness

- **Current stage:** requirements
- **Next stage:** design
- **Ready to design when:** requirements and correctness properties are
  reviewed, the Spec 010 dependency is explicit, and design owners agree which
  artifact sources and administrator command surface must be evaluated.
- **Design-first exception:** no
- **Optional artifacts recommended:** `change-impact.md`, `traceability.md`,
  `verification.md`; add `open-decisions.md` only if command or artifact-source
  decisions remain blocking after design exploration.
- **Downstream review needed:** design, tasks, traceability, verification

## Requirements

### Requirement 1: One Supported Administrator Entrypoint

**User Story:** As a system administrator, I want one documented deployment
entrypoint, so that installation and upgrades do not depend on generated
one-off scripts or manually reconstructed commands.

**Priority:** must-have

#### Acceptance Criteria

1. THE SYSTEM SHALL provide one supported administrator entrypoint for
   protected install, upgrade, deployment status, and rollback operations.
2. WHEN the entrypoint requires root authority, THEN it SHALL either run under
   an explicit elevation mechanism or return one actionable elevation
   instruction without falling back to user-local state.
3. THE ENTRYPOINT SHALL expose stable help, exit status, and machine-readable
   result contracts for automation and troubleshooting.
4. THE SUPPORTED PROCEDURE SHALL NOT require an operator to create or edit a
   deployment Python or shell script.
5. WHERE an acceptance-specific compatibility wrapper remains, THE
   DOCUMENTATION SHALL identify the supported entrypoint as authoritative and
   the wrapper as internal or deprecated.

### Requirement 2: Artifact Identity And Provenance

**User Story:** As a release maintainer, I want deployment inputs bound to an
approved release identity, so that the host cannot activate an ambiguous or
substituted artifact.

**Priority:** must-have

#### Acceptance Criteria

1. GIVEN a local release artifact, WHEN deployment is requested, THEN the
   entrypoint SHALL validate its wheel filename, package metadata, package
   version, SHA-256 digest, and required protected assets before host mutation.
2. GIVEN a published release reference, WHEN it is supported by the chosen
   design, THEN the entrypoint SHALL verify the approved release identity and
   integrity metadata before staging.
3. THE ENTRYPOINT SHALL derive the release manifest from validated inputs and
   SHALL NOT require the operator to hand-author the manifest or digest.
4. IF the artifact, release identity, package version, manifest, protocol
   versions, or digest disagree, THEN deployment SHALL fail before candidate
   installation or protected host mutation.
5. THE DEPLOYMENT EVIDENCE SHALL identify the non-secret artifact provenance,
   digest, release identity, and invoking workflow.

### Requirement 3: Trusted Staging And Cleanup

**User Story:** As a security-conscious administrator, I want deployment inputs
copied into trusted staging, so that world-writable paths and cleanup races
cannot change what is installed.

**Priority:** must-have

#### Acceptance Criteria

1. BEFORE installing a candidate, THE ENTRYPOINT SHALL copy exact validated
   inputs into a private, root-owned staging or evidence boundary and recheck
   their identity after copying.
2. THE SUPPORTED OPERATOR PROCEDURE SHALL NOT depend on persistent artifacts,
   manifests, or scripts under `/tmp`.
3. IF an external source path is used as input, THEN the deployment transaction
   SHALL snapshot it before relying on its contents and SHALL not reread the
   mutable source after snapshot validation.
4. THE ENTRYPOINT SHALL preserve valid artifact filenames required by the
   package installer.
5. WHEN a transaction finishes or fails, THEN bounded temporary staging SHALL
   be removed or retained according to an explicit evidence policy without
   deleting the selected or previous immutable release.
6. IF a staging path is a symlink, unexpectedly writable, outside its allowed
   root, or has untrusted ownership, THEN deployment SHALL fail closed.

### Requirement 4: Preflight-First Transactional Activation

**User Story:** As an operator, I want compatibility and authorization checked
before activation, so that a bad candidate cannot interrupt scheduled
protection.

**Priority:** must-have

#### Acceptance Criteria

1. BEFORE changing a service unit, stable launcher, or selected release, THE
   ENTRYPOINT SHALL verify the staged CLI, backend, tray, packaged assets,
   control protocol, daemonless manifest schema, authorized access, denied
   access, and required timer health.
2. WHEN selecting a release, THE ENTRYPOINT SHALL use a locked
   expected-current compare-and-swap operation.
3. IF the selected release changes after the transaction begins, THEN the
   entrypoint SHALL reject activation rather than overwrite the newer state.
4. THE TRANSACTION SHALL define one mutation boundary after which every
   exception, interruption, termination signal, or failed verification invokes
   recovery.
5. DEPLOYMENT SHALL NOT trigger backup or retention and SHALL preserve active
   and enabled backup and retention scheduling.

### Requirement 5: Verified Rollback And State Preservation

**User Story:** As an administrator, I want a repeatable rollback command, so
that I can recover the prior working release without reconstructing an old
deployment script.

**Priority:** must-have

#### Acceptance Criteria

1. GIVEN a compatible previous release, WHEN rollback is requested, THEN the
   supported entrypoint SHALL probe it before atomically exchanging selected
   and previous release identities.
2. IF activation fails after mutation begins, THEN recovery SHALL restore the
   prior selector and required service state and SHALL verify control-channel
   and timer health.
3. ROLLBACK SHALL preserve protected configuration, credential references,
   schedules, retention enablement, and durable run records.
4. IF no compatible previous release exists, THEN rollback SHALL fail with an
   actionable result and SHALL NOT modify the selected release.
5. A SUCCESSFUL install, upgrade, or rollback result SHALL report the selected
   and previous release identities and the evidence location.

### Requirement 6: Idempotency, Concurrency, And Recovery

**User Story:** As an administrator, I want deployment retries to be safe, so
that interruption or repeated invocation does not corrupt release state.

**Priority:** must-have

#### Acceptance Criteria

1. WHILE another deployment transaction holds the deployment lock, A SECOND
   MUTATING REQUEST SHALL fail without changing host state.
2. GIVEN the same already-selected release and identical verified inputs, WHEN
   deployment is repeated, THEN the entrypoint SHALL return an idempotent
   outcome or perform a no-op verification rather than create ambiguous state.
3. WHEN a stale inert candidate from an interrupted pre-mutation attempt is
   found, THEN the entrypoint SHALL either prove and resume it or remove it
   safely before proceeding.
4. WHEN prior transaction evidence indicates incomplete post-mutation
   recovery, THEN status SHALL report an attention state and mutating commands
   SHALL fail until the state is reconciled.
5. INTERRUPTION handling SHALL be bounded and SHALL never report success
   before post-activation verification completes.

### Requirement 7: Redacted Evidence And Operator Diagnostics

**User Story:** As an administrator, I want concise deployment evidence and
diagnostics, so that I can understand failures without exposing credentials or
reading implementation-specific scratch files.

**Priority:** must-have

#### Acceptance Criteria

1. EVERY mutating transaction SHALL create root-owned evidence containing
   bounded command outcomes, gate results, release identities, timestamps, and
   rollback disposition.
2. THE EVIDENCE AND USER-FACING OUTPUT SHALL NOT contain repository passwords,
   cloud credentials, environment-file contents, raw secret arguments, or
   credential-bearing URLs.
3. WHEN a gate fails, THEN output SHALL identify the failed stage, state
   whether protected mutation began, and provide the evidence location and safe
   next action.
4. THE STATUS OPERATION SHALL report selected and previous releases, transaction
   attention state, one-shot helper readiness, and backup/retention timer health
   without leaving a TimeLocker service process resident.
5. THE ENTRYPOINT SHALL distinguish warnings, failed validation, failed
   activation with successful recovery, and failed recovery through stable
   result codes.

### Requirement 8: Portable Deployment Boundary

**User Story:** As a maintainer, I want platform-neutral deployment contracts,
so that Linux delivery does not embed systemd assumptions into future Windows
support.

**Priority:** should-have

#### Acceptance Criteria

1. THE ARTIFACT, manifest, transaction state, evidence, activation, status, and
   rollback contracts SHALL be platform-neutral.
2. Linux SHALL implement root-owned paths, stable launchers, peer-authorized
   short-lived helpers or one-shot services, and systemd unit/timer verification
   through a Linux adapter.
3. Windows-specific service control, named-pipe authorization, installation
   paths, and elevation SHALL remain behind injectable platform contracts.
4. THIS PACKAGE SHALL NOT claim live Windows deployment until install, upgrade,
   rollback, authorization, interruption, and recovery are accepted on a
   Windows host.
5. WHERE a platform operation is unsupported, THE ENTRYPOINT SHALL fail
   explicitly without partial installation.

### Requirement 9: Zero Idle Service Residency

**User Story:** As an operator, I want TimeLocker to consume no service CPU or
resident memory while idle, so that backup tooling does not waste host
resources or create daemon-specific failure modes.

**Priority:** must-have

#### Acceptance Criteria

1. WHILE no backup, retention, restore, explicit query, or explicit control
   action is running, THE SYSTEM SHALL have no TimeLocker-owned privileged
   process resident.
2. Scheduled backup and retention SHALL execute as bounded one-shot jobs and
   SHALL NOT depend on a continuously resident TimeLocker scheduler or control
   service.
3. Protected queries and manual actions SHALL activate a short-lived
   authenticated helper that exits after one bounded request or operation.
4. Protected workers SHALL atomically publish a sanitized status snapshot that
   an authorized unprivileged tray can read without invoking a privileged
   status service.
5. The optional tray SHALL observe status-file changes directly and SHALL NOT
   require a privileged event socket, heartbeat, or resident event broker.
6. Reading status or run records SHALL NOT itself publish a change event or
   cause an unbounded read-notify-read cycle.
7. Automated and live acceptance SHALL prove zero TimeLocker privileged
   processes and zero TimeLocker service CPU consumption during an idle
   observation interval of at least 90 seconds.

## Correctness Properties

- **CP-001:** No protected selector, service, launcher, or timer mutation occurs
  before artifact identity and all pre-mutation gates pass.
- **CP-002:** A selector changes only from the locked expected-current release
  to the exact compatible candidate, or through a verified selected/previous
  rollback exchange.
- **CP-003:** Any failure or interruption after the mutation boundary either
  restores the prior selected release and required service/timer health or
  leaves a durable attention state that blocks further mutation.
- **CP-004:** Artifact bytes installed into the immutable release are identical
  to the bytes whose digest and metadata were recorded after private staging.
- **CP-005:** Deployment, upgrade, status, and rollback never execute backup,
  retention, restore, or repository-pruning operations.
- **CP-006:** Secret categories remain absent from command output, evidence,
  manifests, and transaction records for every success and failure path.
- **CP-007:** Platform-specific paths, service management, identity, and
  elevation are reachable only through the selected platform adapter.
- **CP-008:** When the set of active protected operations is empty, the set of
  resident TimeLocker-owned privileged processes is also empty.

## Technical Context

- **Language/Version:** Python 3.12 and 3.13
- **Primary Dependencies:** Python packaging, existing immutable-release and
  system-control contracts, operating-system service manager
- **Target Platform:** Linux Mint/systemd acceptance first; portable Windows
  contract retained
- **Constraints:** root-only mutation; offline/local artifact support; no
  credential disclosure; no caller pyenv, home, checkout, or working-directory
  dependency after installation; no resident TimeLocker daemon
- **Performance Goals:** local validation and status should complete promptly;
  network artifact acquisition, when supported, must have explicit timeouts;
  idle privileged CPU and resident memory are both zero

## Success Criteria

- **SC-001:** A documented administrator can install or upgrade a clean Linux
  host using one supported entrypoint without manually creating a manifest,
  digest, or temporary script.
- **SC-002:** The supported entrypoint deploys a validated wheel, reports the
  exact selected and previous releases, and passes installed CLI, backend,
  tray, socket, service, and timer checks.
- **SC-003:** Forced failures at every transaction stage demonstrate no
  pre-boundary mutation and verified post-boundary recovery or attention state.
- **SC-004:** An approved rollback restores the previous compatible release
  while protected configuration, schedules, run records, backup, and retention
  remain intact.
- **SC-005:** Repeated and concurrent deployment attempts satisfy idempotency
  and lock behavior under automated tests and Linux live acceptance.
- **SC-006:** Durable installation, release-management, command-reference, and
  troubleshooting documentation contains no `/tmp`-based operator workflow.
- **SC-007:** Linux live acceptance is recorded; Windows support remains
  explicitly contractual until separately accepted.
- **SC-008:** Linux live acceptance shows no TimeLocker-owned privileged
  process during at least 90 seconds with no protected operation running.

## Resolved Design Decisions

- The supported command is the installed standalone `timelocker-deploy`
  entrypoint with install, upgrade, status, and rollback verbs.
- The accepted initial artifact source is one local wheel.
- Private inputs and retained evidence live below the protected deployment
  evidence root; operator workflows do not use `/tmp`.
- Install and upgrade share one transaction engine and expose separate verbs.
- Linux/systemd is implemented; Windows remains an explicit future platform
  implementation and acceptance boundary.

## Related Artifacts

- Overview: [README.md](./README.md)
- Canonical Context: [canonical-context.md](./canonical-context.md)
- Design: [design.md](./design.md)
- Tasks: [tasks.md](./tasks.md)
- Verification: [verification.md](./verification.md)
