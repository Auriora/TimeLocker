---
title: "Test Template: Generic Test Document"
id: "TEST-template"
type: [ template, testing ]
status: [ draft ]
owner: "{{owner}}" # e.g., QA Team, Lead Tester
last_reviewed: "{{DD-MM-YYYY}}"
tags: [template, testing, qa, tag1, tag2] # Practical tags for organization and search
links:
  tooling: []
---

# Test Template: Generic Test Document

- **Owner**: {{owner}} # e.g., QA Team, Lead Tester
- **Status**: [Draft | In Review | Approved]
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [e.g., QA Team, Developers, Stakeholders]
- **Scope**: [e.g., Entire project, specific module, feature X]

## 1. Purpose

[Establish the objectives, quality targets, and gating criteria for this test document. Clearly state the objective and scope.]

## 2. Key Information

[Provide a summary of the document's content, such as the test matrix for a strategy, or test steps for a test case.]

### 2.1. Test Matrix (for Strategies)

| Level       | Purpose                         | Tooling                                  | Owner                    |
|-------------|---------------------------------|------------------------------------------|--------------------------|
| Unit        | [e.g., Baseline correctness]    | [e.g., pytest, vitest]                   | [e.g., Development Team] |
| Integration | [e.g., Component interaction]   | [e.g., API tests, end-to-end frameworks] | [e.g., QA Team]          |
| End-to-End  | [e.g., User journey validation] | [e.g., Playwright, Cypress]              | [e.g., QA Team]          |

### 2.2. Test Steps (for Test Cases)

| Step # | Description | Expected Result    |
|--------|-------------|--------------------|
| 1      | [Action]    | [Expected Outcome] |

## 3. Environments

[List required testing environments, data fixtures, and any necessary access credentials (redacted).]

## 4. Automation

[Describe CI jobs and triggers related to testing. Specify expectations for reporting and artifacts.]

## 5. Manual Validation

[Document any exploratory or manual testing steps that supplement automation.]

## 6. Risks & Mitigations

[Highlight known gaps in testing, potential risks, and planned mitigations.]

<!-- Add more numbered sections as needed, e.g., ## 7. [Another Section Title] -->

# References

- Link to additional resources, specifications, or related tickets.
