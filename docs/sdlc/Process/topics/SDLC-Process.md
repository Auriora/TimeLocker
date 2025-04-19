# SDLC Process

Below is an updated SDLC process that takes into account the existing WriterSide SRS document (located in docs/sdlc/SRS/) and guides development with clear review checkpoints. In addition to the process phases, sample AI LLM chat prompts are provided for initiating review requests of each key deliverable.

---

### 1. Requirements Gathering & Analysis
- **Objective:**
  Ensure that all requirements—including those specific for a Desktop GUI—are clearly understood and agreed upon. The SRS document in docs/sdlc/SRS/ is the foundation, so its content (e.g., traceability matrices, external interface definitions, usability and security requirements) will be referenced throughout this process.

- **Activities:**
  - Review and confirm requirements provided in the existing SRS.
  - Identify additional requirements relevant to UX/UI and Desktop GUI functionality.
  - Update or add user stories and acceptance criteria as needed.

- **Documentation Produced:**
  - Requirements Confirmation Document (with annotations linking back to the SRS).
  - Updated user stories and acceptance criteria (if applicable).

- **Checkpoint & Sample Review Prompt:**
  - **Prompt for Requirements Confirmation Document:**
```
Hi Junie, please generate a Requirements Confirmation Document that summarizes the key functional and non-functional requirements from the SRS (located in docs/sdlc/SRS/). Ensure that it covers requirements for external interfaces, security, usability, and performance. Once done, please share the document for review and feedback.
```


---

### 2. UX & UI Design
- **Objective:**
  Define the user experience flows and visual presentation of the Desktop GUI application.

- **Activities:**
  - **UX Design:**
    - Develop and review user journeys and interaction flows.
    - Create wireframes or low-fidelity prototypes.
  - **UI Design:**
    - Produce high-fidelity mockups for primary screens.
    - Develop a UI style guide addressing visual elements, themes, colors, typography, and iconography.

- **Documentation Produced:**
  - UX Documentation: User journey maps, wireframes, and usability prototypes.
  - UI Documentation: High-fidelity mockups and a detailed UI style guide.

- **Checkpoint & Sample Review Prompts:**
  - **For UX Artifacts:**
```
Hi Junie, please create a set of wireframes and user journey maps for the Desktop GUI application, ensuring that the user flows align with the requirements stated in the SRS. Share these UX artifacts so that I can review the proposed user interactions and suggest any tweaks.
```

  - **For UI Artifacts:**
```
Hi Junie, please generate high-fidelity UI mockups along with a detailed style guide for our application. The style guide should include color palettes, typography choices, and UI component guidelines. Once complete, please present the mockups and style guide for my review and approval.
```


---

### 3. Design Phase
- **Objective:**
  Develop a technical design that integrates system architecture with the approved UX/UI designs.

- **Activities:**
  - Establish the high-level architecture with UML diagrams, including integration of UI elements with backend components.
  - Draft detailed design documentation outlining module designs, interfaces, database schemas, and how approved UI components are to be implemented.
  - Review design constraints, safety/security requirements, and external interface details as referenced in the SRS.

- **Documentation Produced:**
  - Architecture Design Document (with UML/Flow diagrams).
  - Detailed Design Specification Document (module descriptions, interface definitions, and integration details).

- **Checkpoint & Sample Review Prompt:**
  - **Prompt for Design Documents:**
```
Hi Junie, please produce the Architecture Design Document and Detailed Design Specification that combine our system's technical design with the approved UX and UI designs. Ensure that the document references the relevant sections of the SRS (including interfaces, security, and usability requirements). Once complete, share these documents for my review.
```


---

### 4. Implementation / Development
- **Objective:**
  Convert approved designs into actual code while aligning with security, quality, and usability standards defined in the SRS.

- **Activities:**
  - Set up the development environment using Python 3.12.3 with virtualenv.
  - Iteratively develop features with reference to the approved UX/UI and design documents.
  - Ensure code quality through internal code reviews and version control commits.
  - Integrate UI components based on approved mockups.

- **Documentation Produced:**
  - Code documentation and inline comments.
  - Updated design changes (if any) and commit change logs.

- **Checkpoint & Sample Review Prompt:**
  - **Prompt for Code Review:**
```
Hi Junie, please prepare a summary of the recent code commits related to the UI integration and key features. Include commentary on how the design documents have been followed. Share this summary and associated code documentation so I can review and ensure everything is aligned with our approved plans.
```


---

### 5. Testing
- **Objective:**
  Confirm that the application meets functional, performance, and usability requirements, including those specified in the SRS.

- **Activities:**
  - **Unit Testing:** Develop unit tests for isolated components.
  - **Integration Testing:** Verify that the GUI and backend components work seamlessly.
  - **System Testing:** Validate the end-to-end functionality in an environment that simulates production.
  - **User Acceptance Testing (UAT):** Provide a testable version focusing on user interactions and GUI responsiveness.

- **Documentation Produced:**
  - Test Plans and Test Case Documents.
  - Automated and Manual Test Reports.
  - UAT Feedback and Issue Logs.

- **Checkpoint & Sample Review Prompt:**
  - **Prompt for Testing Deliverables:**
```
Hi Junie, please compile the Test Plan and associated Test Case Documents, including reports from our unit, integration, and system tests. Also, share the UAT feedback documentation so I can review the overall test coverage and user feedback. Let me know if any critical issues are present.
```


---

### 6. Deployment
- **Objective:**
  Roll out the application to a production-like environment after verifying readiness based on design and testing criteria.

- **Activities:**
  - Develop a comprehensive deployment plan that includes rollback procedures and contingency measures.
  - Deploy to a staging environment for final verification.
  - Conduct performance validation and verify UI consistency in this environment.

- **Documentation Produced:**
  - Deployment Plan.
  - Staging Environment Test Reports.
  - Rollback and Contingency Procedures.

- **Checkpoint & Sample Review Prompt:**
  - **Prompt for Deployment Documents:**
```
Hi Junie, please generate the Deployment Plan along with staging environment test reports. Ensure the documentation includes rollback procedures and performance validation results. Once complete, present these documents for my final review and sign-off on the production deployment.
```


---

### 7. Maintenance & Continuous Improvement
- **Objective:**
  Ensure that the application remains robust, secure, and responsive post-deployment while incorporating continuous feedback.

- **Activities:**
  - Monitor application performance, usability logs, and feedback channels.
  - Track and document maintenance issues, enhancements, and version updates.
  - Periodically review the maintenance logs and assess opportunities for improvements.

- **Documentation Produced:**
  - Maintenance and Change Logs.
  - Post-Deployment Review Reports.
  - Updated version-controlled documentation as enhancements are implemented.

- **Checkpoint & Sample Review Prompt:**
  - **Prompt for Maintenance Reviews:**
```
Hi Junie, please compile the most recent Maintenance Log and Post-Deployment Review Report, highlighting any issues observed and enhancements planned. Share these documents for my periodic review to ensure the application remains aligned with its performance, security, and usability goals.
```


---

### Additional Considerations
- **Cross-Referencing the SRS:**
  Throughout the process, ensure that key deliverables (especially design and testing artifacts) reference the original SRS located in docs/sdlc/SRS/. This includes traceability matrices, usability criteria, security controls, and other specifics detailed in the SRS.

- **Using AI LLM (Junie) Effectively:**
  The provided sample prompts are designed to help you initiate review sessions with Junie and obtain detailed, context-specific documentation. Adjust the prompts as needed based on evolving project needs or feedback.

By embedding these review checkpoints and sample AI LLM chat prompts into the SDLC, the process mirrors how a full-fledged software development team would work—ensuring thorough documentation, rigorous validations, and iterative approvals at every stage. Please let me know if you need any more adjustments or additional details in any phase!