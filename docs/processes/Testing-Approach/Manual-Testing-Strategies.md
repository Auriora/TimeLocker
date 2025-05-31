# Manual Testing Strategies

Even with automation, manual testing remains essential for discovering issues that automated tests might miss. For solo developers, efficient manual testing
maximizes quality with limited resources.

## Why It Matters

For solo developers, strategic manual testing:

- Discovers unexpected issues not covered by automated tests
- Evaluates the actual user experience and flow
- Validates that implementation meets design intentions
- Identifies usability problems before users encounter them
- Helps determine what's worth automating

## Key Manual Testing Approaches

### 1. Exploratory Testing

Simultaneously learn, design tests, and execute them:

- Set a time box (30-60 minutes)
- Focus on a specific feature
- Document findings as you go
- Follow interesting paths as they emerge

### 2. Scenario-Based Testing

Verify complete user workflows:

- Create realistic user scenarios
- Include both happy paths and error paths
- Test from the user's perspective
- Verify all steps in the workflow

### 3. Usability Testing

Evaluate how easy the application is to use:

- Assess navigation and flow
- Check for consistency in design
- Verify feedback and error messages
- Test accessibility features

### 4. Dogfooding

Use your own application regularly:

- Incorporate it into your actual workflow
- Perform real tasks, not just test scenarios
- Note any friction or frustration points
- Pay attention to performance in real usage

## Effective Techniques

### Session-Based Testing

Structure exploratory testing into focused sessions:

```
CHARTER: Explore the user registration process
DURATION: 60 minutes
FOCUS AREAS:
- Form validation
- Error messages
- Password requirements
- Account creation confirmation
```

### Heuristic-Based Testing

Use mental shortcuts to guide your testing:

**CRUD**: Test Create, Read, Update, Delete operations

- Example: For contacts, test adding, viewing, editing, and deleting

**SFDPOT**: Structure, Function, Data, Platform, Operations, Time

- Test how data is structured, functions work, data is processed, etc.

## Documentation

Keep it lightweight but useful:

```
Date: 2023-06-15
Feature: User Profile
Approach: Exploratory
Duration: 45 minutes

Areas covered:
- Profile information update
- Password change
- Profile picture upload

Issues found:
1. Profile picture upload fails for PNG files > 2MB
2. No error message when password confirmation doesn't match
```

## Balancing Manual and Automated Testing

- **Automate**: Repetitive tests, regression tests, performance tests
- **Manually test**: Complex scenarios, usability, exploratory areas

## Common Pitfalls

- **Confirmation bias**: Only looking for evidence that software works
    - *Solution*: Actively try to break the application

- **Inconsistent testing**: Testing differently each time
    - *Solution*: Use checklists and structured approaches

- **Shallow testing**: Only testing the happy path
    - *Solution*: Deliberately test edge cases and error conditions

## Practical Tips

- Test early and often during development
- Create reusable checklists for common features
- Vary your testing approaches to find different issues
- Test on different devices and browsers
- When possible, get someone else to try your application
- Schedule dedicated time for focused testing sessions
