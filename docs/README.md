# TimeLocker Documentation

## Overview

TimeLocker is a high-level interface over Restic that centralizes repository management, snapshot operations, and credential handling for reliable backups
across local, S3, and B2 backends. This documentation hub groups user guides, architecture notes, implementation details, and project status artifacts so
contributors and operators can navigate the knowledge base quickly.

## 📋 Documentation Structure

### Primary Documents (Start Here)

- **[Installation Guide](./guides/user/installation.md)** – End-to-end setup for TimeLocker and its dependencies.
- **[Repository Management Guide](./guides/user/repository-management-guide.md)** – Working with named repositories, defaults, and CLI usage patterns.
- **[S3-Compatible Services](./guides/user/s3-compatible-services.md)** – How to configure MinIO, Wasabi, Backblaze B2 (S3 API), and other compatible endpoints.
- **[Testing Quick Start](./4-testing/quickstart-testing.md)** – Fast path for verifying environments, running MinIO integration tests, and interpreting
  results.
- **[Tasks-to-Issues Map](./0-project-management/tasks-to-issues-map.md)** – Canonical mapping between documentation sources and tracked GitHub issues.
- **[Updates Index](./updates/index.md)** – Chronological log of implementation notes and rule applications.

### Supporting Collections

- **Requirements** – [./1-requirements/README.md](./1-requirements/README.md)
- **Architecture** – [./2-architecture/README.md](./2-architecture/README.md)
- **Implementation** – [./3-implementation/README.md](./3-implementation/README.md) and [command-builder.md](./3-implementation/command-builder.md)
- **Testing** – [./4-testing/README.md](./4-testing/README.md) plus MinIO guides under the same directory.
- **Developer Guides** – [./guides/developer/README.md](./guides/developer/README.md), including automation and scheduling playbooks.
- **Processes** – [./processes/README.md](./processes/README.md) and [version-management.md](./processes/version-management.md) for release governance.
- **Reference** – [./reference/README.md](./reference/README.md) and supporting specs such
  as [timelocker-cli-command-hierarchy.md](./reference/timelocker-cli-command-hierarchy.md) and [repository-uri-guide.md](./reference/repository-uri-guide.md).
- **Reports & Updates** – Generated analyses and change logs under [./reports/](./reports/README.md) and [./updates/](./updates/index.md).
- **Archive** – [./archive/README.md](./archive/README.md) – Historical documentation preserved for reference.

## 🚀 Quick Start

### Operating TimeLocker

1. Follow the [Installation Guide](./guides/user/installation.md) to prepare the runtime environment.
2. Create and manage repositories with the [Repository Management Guide](./guides/user/repository-management-guide.md).
3. Configure S3-compatible endpoints using [S3-Compatible Services](./guides/user/s3-compatible-services.md);
   use [guide-minio-testing.md](./4-testing/guide-minio-testing.md) for MinIO specifics.
4. Validate the setup via [Testing Quick Start](./4-testing/quickstart-testing.md) and the MinIO checklist (`checklist-minio-testing.md`).

### Contributing & Maintenance

1. Review current initiatives in [Tasks-to-Issues Map](./0-project-management/tasks-to-issues-map.md) and the latest [updates entry](./updates/index.md).
2. Consult [cli_helpers_extraction.md](./plans/cli_helpers_extraction.md) and other plans for active refactors or feature work.
3. Follow house style from [guides/ai-agent/](./guides/ai-agent/README.md) when authoring new documentation or automation.
4. Capture changes in `docs/updates/` using the [update template](./updates/_template.md).

## 📊 Project Status Summary

- **Latest Status**: [Phase 1 Completion Status Report](./reports/2025-11-08-082339-phase1-completion-status.md) - Phase 1 Foundation Services 100% complete!
- **Implementation Notes**: See [updates index](./updates/index.md) for the most recent change logs, including the [Repository Manager Implementation](./updates/2025-11-08-082339-repository-manager-implementation.md).
- **Open Work Queue**: [Tasks-to-Issues Map](./0-project-management/tasks-to-issues-map.md) is the authoritative crosswalk between docs and GitHub issues.
- **Active Plans**: The [plans directory](./plans/README.md) tracks approved execution plans; update or add entries before large initiatives.

## 🎯 Next Implementation Focus

Refer to the newest update in [docs/updates](./updates/index.md) and any active plan documents (
e.g., [cli_helpers_extraction.md](./plans/cli_helpers_extraction.md)) to confirm current priorities. Align new work with the mapped GitHub issues to keep
traceability intact.

## 🏗️ Architecture Overview

- High-level architecture and deployment topology: [./2-architecture/README.md](./2-architecture/README.md)
- Detailed module breakdowns and code tours: [./3-implementation/README.md](./3-implementation/README.md)
- CLI command structure and hierarchy: [timelocker-cli-command-hierarchy.md](./reference/timelocker-cli-command-hierarchy.md)
- Credential and repository flow summaries: see user guides in `./guides/user/` and testing artifacts in `./4-testing/`.

## 🧪 Testing

- **Quick Start**: [quickstart-testing.md](./4-testing/quickstart-testing.md)
- **MinIO Environment**: [guide-minio-testing.md](./4-testing/guide-minio-testing.md), [summary-minio-setup.md](./4-testing/summary-minio-setup.md),
  and [checklist-minio-testing.md](./4-testing/checklist-minio-testing.md)
- **Coverage Improvements**: [report-test-case-coverage-improvements-pr66.md](./reports/report-test-case-coverage-improvements-pr66.md)
- Execute pytest suites as documented in the testing quick start to validate environments and changes.

## 🔧 Development Setup

- System prerequisites, installation, and command verification: [installation.md](./guides/user/installation.md)
- Automation patterns and scheduling examples: [automation-examples.md](./guides/developer/automation-examples.md)
  and [scheduling-guide.md](./guides/developer/scheduling-guide.md)
- Version bumping workflow: [version-management.md](./processes/version-management.md)
- Reference the root `README.md` for repository layout, dependencies, and standard project setup.

## 📚 Key Reference Areas

| Topic                           | Location              |
|---------------------------------|-----------------------|
| User workflows & FAQs           | `./guides/user/`      |
| Developer operations            | `./guides/developer/` |
| Requirements & personas         | `./1-requirements/`   |
| Architecture decisions          | `./2-architecture/`   |
| Implementation conventions      | `./3-implementation/` |
| Testing strategy                | `./4-testing/`        |
| Operational processes           | `./processes/`        |
| Formal reports                  | `./reports/`          |
| Updates & changelog supplements | `./updates/`          |
| Historical documentation        | `./archive/`          |

## 🔮 Roadmap

- Planned refactors and feature work are curated in [plans/](./plans/README.md) and synchronized with the GitHub issue backlog
  via [tasks-to-issues-map.md](./0-project-management/tasks-to-issues-map.md).
- Historical context and completed milestones live in archived updates and reports; review the updates index before starting new initiatives.

## 📞 Support

- **Documentation Gaps**: File new entries in [updates](./updates/index.md) and cross-link to `docs/updates/_template.md`.
- **Agent & Automation Guidance**: Follow the protocols in [guides/ai-agent/](./guides/ai-agent/README.md).
- **Technical Questions**: Use the appropriate guide (user vs developer) and reference materials under `./reference/`.

---

## 📋 Documentation Maintenance

1. Keep [updates/index.md](./updates/index.md) current; every substantial change needs a companion entry from the [update template](./updates/_template.md).
2. When relocating documentation, update cross-links and references (see `AGENT-RULE-Documentation-Conventions`).
3. Ensure new documents include metadata consistent with their directory’s README and templates (e.g., `docs/_template/`).
4. Align ongoing work with the authoritative mappings in [tasks-to-issues-map.md](./0-project-management/tasks-to-issues-map.md) to preserve traceability.

*Last Updated: 2025-11-08*