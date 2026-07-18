# Tasks-to-Issues Mapping

Last verified: 2026-07-18

GitHub issue state is authoritative. This file is a dated navigation snapshot for repository readers; refresh it from live GitHub before using it for planning or
release decisions.

Repository: [Auriora/TimeLocker](https://github.com/Auriora/TimeLocker)

Snapshot: 23 open and 7 closed issues in the original #5-#34 project queue.

## Open Issues

### CLI and Snapshots

- [#5](https://github.com/Auriora/TimeLocker/issues/5) — Implement missing functionality for stub commands. Context: [CLI consolidation plan](../plans/2026-04-23-173102-cli-consolidation-stabilization-plan.md).
- [#7](https://github.com/Auriora/TimeLocker/issues/7) — Improve error messages for invalid commands and parameters. Context: [CLI command hierarchy](../reference/timelocker-cli-command-hierarchy.md).
- [#8](https://github.com/Auriora/TimeLocker/issues/8) — Create comprehensive tests for the CLI command structure. Context: [Testing documentation](../4-testing/README.md).
- [#9](https://github.com/Auriora/TimeLocker/issues/9) — Implement command aliases through separate command definitions. Context: [CLI command hierarchy](../reference/timelocker-cli-command-hierarchy.md).
- [#11](https://github.com/Auriora/TimeLocker/issues/11) — Implement multi-repository defaults for snapshot commands. Context: [CLI command hierarchy](../reference/timelocker-cli-command-hierarchy.md).
- [#13](https://github.com/Auriora/TimeLocker/issues/13) — Update shell completion scripts for the current command hierarchy. Context: [CLI command hierarchy](../reference/timelocker-cli-command-hierarchy.md).
- [#15](https://github.com/Auriora/TimeLocker/issues/15) — Optimize CLI loading for large command sets. Context: [Performance guide](../guides/developer/performance-optimization-guide.md).
- [#29](https://github.com/Auriora/TimeLocker/issues/29) — Implement snapshot content and path search. Context: [CLI command hierarchy](../reference/timelocker-cli-command-hierarchy.md).
- [#33](https://github.com/Auriora/TimeLocker/issues/33) — Implement interactive mode. Context: [CLI command hierarchy](../reference/timelocker-cli-command-hierarchy.md).
- [#34](https://github.com/Auriora/TimeLocker/issues/34) — Complete advanced snapshot diff functionality. Context: [CLI command hierarchy](../reference/timelocker-cli-command-hierarchy.md).

### Documentation and Release

- [#17](https://github.com/Auriora/TimeLocker/issues/17) — Prepare user guides and API documentation. Context: [Documentation status](../DOCUMENTATION-STATUS.md).
- [#22](https://github.com/Auriora/TimeLocker/issues/22) — Prepare the PyPI distribution. Context: [Version management](../processes/version-management.md).
- [#23](https://github.com/Auriora/TimeLocker/issues/23) — Finalize release notes and changelog. Context: [Version management](../processes/version-management.md).
- [#24](https://github.com/Auriora/TimeLocker/issues/24) — Set up version tagging and release process. Context: [Version management](../processes/version-management.md).
- [#25](https://github.com/Auriora/TimeLocker/issues/25) — Verify installation in clean environments. Context: [Installation guide](../guides/user/installation.md).

### Performance and Testing

- [#18](https://github.com/Auriora/TimeLocker/issues/18) — Profile and optimize file-selection algorithms. Context: [Performance guide](../guides/developer/performance-optimization-guide.md).
- [#19](https://github.com/Auriora/TimeLocker/issues/19) — Improve backup progress-reporting efficiency. Context: [Performance guide](../guides/developer/performance-optimization-guide.md).
- [#20](https://github.com/Auriora/TimeLocker/issues/20) — Optimize memory use for large operations. Context: [Performance guide](../guides/developer/performance-optimization-guide.md).
- [#21](https://github.com/Auriora/TimeLocker/issues/21) — Add performance benchmarks to the test suite. Context: [Testing documentation](../4-testing/README.md).

### Services and Features

- [#28](https://github.com/Auriora/TimeLocker/issues/28) — Integrate credential services with the CLI and per-repository secrets. Context: [Per-repository credentials](../guides/user/per-repo-credentials.md).
- [#30](https://github.com/Auriora/TimeLocker/issues/30) — Implement enhanced configuration-service operations. Context: [Service-layer integration](../3-implementation/service-layer-integration.md).
- [#31](https://github.com/Auriora/TimeLocker/issues/31) — Implement scheduling services for automated backups. Context: [Scheduling system](../2-architecture/scheduling-system.md).
- [#32](https://github.com/Auriora/TimeLocker/issues/32) — Implement backup completion and error notifications. Context: [Component breakdown](../2-architecture/component-breakdown.md).

## Closed Issues

- [#6](https://github.com/Auriora/TimeLocker/issues/6) — Validate snapshot IDs and repository names — closed 2025-09-28.
- [#10](https://github.com/Auriora/TimeLocker/issues/10) — Enforce `file://` validation for repository URIs — closed 2025-09-28.
- [#12](https://github.com/Auriora/TimeLocker/issues/12) — Update user documentation for the current CLI — closed 2025-09-28.
- [#14](https://github.com/Auriora/TimeLocker/issues/14) — Create the old-command migration guide — closed 2025-09-29.
- [#16](https://github.com/Auriora/TimeLocker/issues/16) — Audit README and installation documentation — closed 2025-09-28.
- [#26](https://github.com/Auriora/TimeLocker/issues/26) — Monitor CI workflows after modernization — closed 2025-09-29.
- [#27](https://github.com/Auriora/TimeLocker/issues/27) — Remove references to old installation methods — closed 2025-09-28.

## Maintenance

1. Refresh the counts, issue states, titles, and verification date from live GitHub at least monthly and before release.
2. Keep durable implementation context in current repository documents; do not link active issues to removed milestone files.
3. When an issue closes, retain it in the closed section for one release cycle, then move older issue history to an archived status report if needed.
4. Add newly created issues when they become part of the current project queue; issue numbers above #34 are intentionally outside this historical queue unless
   explicitly added during a future review.
