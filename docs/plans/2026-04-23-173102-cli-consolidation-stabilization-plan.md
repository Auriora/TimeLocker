---
title: "RFC: CLI Consolidation Stabilization Plan"
id: "rfc-2026-04-23-173102-cli-consolidation-stabilization-plan"
type: [ plan ]
status: [ accepted ]
owner: "Codex"
last_reviewed: "23-04-2026"
tags: [plan, cli, consolidation, service-layer, configuration, monitoring]
links:
  tooling: [pytest, python-agent-ide]
---

# RFC: CLI Consolidation Stabilization Plan

- **Owner**: Codex
- **Status**: Accepted
- **Last Updated**: 23-04-2026
- **Created Date**: 23-04-2026
- **Audience**: Engineering Teams, Reviewers

## 1. Purpose

Stabilize the TimeLocker CLI composition layer by reducing duplicate registration paths, narrowing compatibility seams, and defining an execution order for
config, repository resolution, and monitoring cleanup.

Success criteria:

- top-level command registration follows a consistent pattern for each command family
- CLI help and command discovery stay stable while consolidation proceeds
- command modules converge on one config path and one repository-resolution path
- `CLIServiceManager` shrinks toward a compatibility boundary instead of remaining the logic hub

## 2. Problem Statement

The CLI currently mixes multiple integration styles:

- `src/TimeLocker/cli.py` owns some Typer apps directly and also imports modular apps from `src/TimeLocker/cli_modules/commands/`
- some command families merge command registrations into predeclared root apps, while others are mounted as standalone Typer apps
- CLI command code mixes `ConfigurationModule`, `ConfigService`, `CLIServiceManager`, and direct utility imports for repository resolution
- monitoring behavior spans command modules plus a CLI-only monitoring integration wrapper

These overlaps increase regression risk for help output, command registration, and runtime behavior.

## 3. Proposed Solution

Implement the consolidation in bounded slices:

1. CLI composition
   - add a single merge helper in `src/TimeLocker/cli.py`
   - remove duplicate security-app mounting by merging modular security commands into the predeclared root `security_app`
   - add a regression test that top-level command names remain unique
2. Config path cleanup
   - standardize CLI-facing commands on `ConfigService`
   - isolate or remove legacy direct `ConfigurationModule` usage from CLI command code
3. Repository-resolution cleanup
   - standardize CLI-facing commands on `cli_modules.services.RepositoryResolver`
   - remove direct repository-resolver utility imports from command modules where a wrapper exists
4. `CLIServiceManager` reduction
   - keep `get_cli_service_manager()` stable while moving domain logic out of `CLIServiceManager`
   - prefer facade or narrow service adapters over manager-internal fallbacks
5. Monitoring consolidation
   - reduce overlap between `monitor.py`, `monitoring.py`, and `CLIMonitoringIntegration`
   - converge on one command-facing formatting/integration path
6. Documentation sync
   - update implementation and reference docs after the code structure settles

## 4. Alternatives

- Large one-pass CLI rewrite
  This would produce too much churn and make help-tree regressions harder to isolate.
- Leave the current compatibility layers in place
  This avoids immediate risk but preserves the exact registration and abstraction drift causing the current maintenance problem.

## 5. Impact

- Affected systems or teams
  CLI command authors, service-layer maintainers, and test maintainers
- Risks and mitigations
  Help-tree regressions are the main near-term risk.
  Mitigation: keep the first slice focused on registration only and validate with targeted CLI help tests.
- Migration or rollout plan
  Land small slices in the order listed below, with tests after each slice.

## 6. Task Set

1. Normalize the root CLI registration helper in `src/TimeLocker/cli.py`
   Status: Completed on 2026-04-23
   Success check: hybrid command groups use one merge helper instead of repeated manual append loops.
2. Remove duplicate security command-group mounting
   Status: Completed on 2026-04-23
   Success check: `security` is mounted once at the root and modular commands are merged into the existing app.
3. Add a regression test for unique top-level command names
   Status: Completed on 2026-04-23
   Success check: CLI help tests fail if duplicate root registrations reappear.
4. Standardize CLI command modules on `ConfigService`
   Status: Pending
   Success check: no new command code instantiates `ConfigurationModule` directly outside explicit compatibility helpers.
5. Standardize CLI command modules on `RepositoryResolver`
   Status: Pending
   Success check: command modules stop mixing wrapper-based resolution with direct utility imports.
6. Reduce `CLIServiceManager` fan-out
   Status: Pending
   Success check: command modules access narrower service seams rather than manager internals.
7. Consolidate monitoring command and integration paths
   Status: Pending
   Success check: one monitoring command-facing integration path remains.
8. Refresh docs and trace execution
   Status: In Progress
   Success check: update plan and update-log entries exist for each landed slice.

## 7. Initial Execution Notes

The first implementation slice intentionally targeted the safest high-value inconsistency:

- `security_app` was pre-mounted in `src/TimeLocker/cli.py` and later a second modular `security` app was mounted again
- this slice replaces the duplicate mount with the same merge model already used by other hybrid command groups
- the change also introduces a single merge helper so future composition cleanup can reuse one code path

# References

- `src/TimeLocker/cli.py`
- `src/TimeLocker/cli_services.py`
- `src/TimeLocker/cli_modules/commands/base.py`
- `src/TimeLocker/cli_modules/services/config_service.py`
- `src/TimeLocker/cli_modules/services/repository_resolver.py`
- `src/TimeLocker/cli_modules/monitoring_integration.py`
- `docs/reference/repo-orientation-and-change-map.md`
- `docs/3-implementation/service-layer-integration.md`
