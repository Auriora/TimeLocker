---
title: "Report: Security Review"
id: "SEC-{{id}}"
type: [ report ]
status: [ draft | in_review | approved ]
owner: "{{owner}}" # e.g., Author, Reporting Team
last_reviewed: "{{DD-MM-YYYY}}"
tags: [report, security] # Practical tags for organization and search
links:
  tooling: []
  threat_model: []
---

# Report: Security Review

- **Owner**: {{owner}} # e.g., Author, Reporting Team
- **Status**: [Draft | In Review | Approved]
- **Created Date**: DD-MM-YYYY
- **Last Updated**: {{DD-MM-YYYY}}
- **Audience**: [e.g., Stakeholders, Engineering Teams, QA]
- **Scope**: {{scope_description}} (e.g., repository, module, release tag)

## 1. Purpose

This report provides an executive summary of the security review, including its scope and overall risk level. Clearly state the objective and scope of this
report.

## 2. Detailed Findings

### Executive Summary

- Overall risk level: {{overall_risk_level}} (Low / Medium / High)
- Short summary of highest priority findings and recommended next steps.

### Findings

Provide a concise table of findings discovered during the review. Include links to evidence (scan outputs, line numbers, PRs).

| ID      | Severity | Title                      | Details                                  | Recommendation                                         |
|---------|----------|----------------------------|------------------------------------------|--------------------------------------------------------|
| SEC-001 | High     | Example: Hard-coded secret | Detected an AES key in config.py line 42 | Rotate secret, add secrets manager, add detection rule |

Guidance for populating this table:

- ID: unique identifier (SEC-###)
- Severity: High / Medium / Low (use your project scoring rubric)
- Title: short, descriptive
- Details: short description, file/path, evidence link
- Recommendation: immediate remediation or mitigation steps

### Reproduction / How this was found

- Static analysis: e.g., `bandit -r src/ -lll` (attach output or artifact link)
- SCA / dependency scanning: e.g., `dependency-check` or GitHub Dependabot alerts
- Manual review notes: list pages/PRs where the issue was observed

## 3. Recommendations

### Remediation Plan

List prioritized remediation tasks with owners, estimate, and due date.

- **Action 1**: SEC-001: Remove hard-coded secret, rotate credentials, add secret scanning rule. Owner: @security. ETA: {{due_date}}
- **Action 2**: SEC-002: Fix insecure TLS configuration in service X. Owner: @infra. ETA: {{due_date}}

Track progress by linking PRs and verifying fixes in follow-up scans.

# References

### Severity definitions

- High: Immediate action required (remote code execution, credential exposure, high-impact privilege escalation).
- Medium: Important but not immediately exploitable; schedule within sprint cycle.
- Low: Informational or low-impact; monitor and address as capacity allows.

### Notes & References

- Attach scan artifacts (links to CI job artifacts, SARIF, bandit output) in `links:` frontmatter where possible.
- Recommended tools: Bandit, Semgrep, Snyk/Dependabot/OSV, Trivy (for containers), OWASP Dependency-Check.
- Consider adding periodic security review cadence (quarterly) and recording reviews in `docs/reports/updates/`.
