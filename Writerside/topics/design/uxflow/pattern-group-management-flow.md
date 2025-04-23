# Pattern Group Management Flow

This document details the Pattern Group Management Flow for the TimeLocker application, which allows users to create and manage file inclusion/exclusion patterns for their backups.

## Flow Objective

The Pattern Group Management Flow aims to:
- Enable users to create reusable groups of file inclusion/exclusion patterns
- Provide tools for testing patterns against sample file paths
- Allow modification of existing pattern groups
- Support applying pattern groups to backup configurations
- Facilitate sharing patterns between backup configurations

## Entry Points

Users enter this flow when:
- Selecting "Manage Patterns" from the settings menu
- Creating or editing patterns during backup configuration
- Accessing pattern management from advanced settings
- Importing pattern groups from external sources

## Flow Diagram

```
@startuml
actor "User" as U
participant "Dashboard" as D
participant "Pattern Manager" as PM
participant "Pattern Editor" as PE
participant "Backup Manager" as BM

note over U, BM: Pattern Group Management Flow
U -> D: Select "Manage Patterns"
D -> PM: Open pattern manager
PM -> BM: Request pattern groups
BM --> PM: Return pattern groups
PM -> U: Display pattern group list

note over U, BM: Create Pattern Group
U -> PM: Select "Create Pattern Group"
PM -> PE: Open pattern editor
U -> PE: Enter pattern group name
U -> PE: Add inclusion patterns
U -> PE: Add exclusion patterns
U -> PE: Save pattern group
PE -> BM: Store new pattern group
BM --> PE: Confirmation
PE --> PM: Update pattern group list
PM -> U: Display updated list

note over U, BM: Edit Pattern Group
U -> PM: Select existing pattern group
PM -> PE: Load pattern group details
PE -> U: Display editable patterns
U -> PE: Modify patterns
U -> PE: Save changes
PE -> BM: Update pattern group
BM --> PE: Update confirmation
PE --> PM: Return to pattern list
PM -> U: Display updated pattern group

note over U, BM: Delete Pattern Group
U -> PM: Select pattern group to delete
PM -> U: Display confirmation dialog
U -> PM: Confirm deletion
PM -> BM: Request pattern group removal
BM --> PM: Removal status
PM -> U: Display updated pattern list
@enduml
```

## Step-by-Step Flow: Creating a Pattern Group

| Step # | Actor | Action | System Response | UI Elements | Notes |
|--------|-------|--------|-----------------|------------|-------|
| 1 | User | Selects "Manage Patterns" from settings | System opens pattern management interface | Pattern group list | Shows existing pattern groups with usage count |
| 2 | User | Selects "Create Pattern Group" | System opens pattern editor | Pattern editor with empty fields | Provides pattern syntax guidance |
| 3 | User | Enters pattern group name | System validates name | Name field with validation | Ensures unique, valid name |
| 4 | User | Adds inclusion patterns | System validates pattern syntax | Pattern input with syntax highlighting | Supports glob patterns with auto-completion |
| 5 | User | Adds exclusion patterns | System validates pattern syntax | Pattern input with syntax highlighting | Suggests common exclusions (temp files, caches) |
| 6 | User | Tests patterns against sample paths | System shows matching results | Pattern test tool with sample results | Helps verify pattern behavior |
| 7 | User | Saves pattern group | System stores new pattern group | Save button, success notification | New group immediately available for use |

## Step-by-Step Flow: Editing a Pattern Group

| Step # | Actor | Action | System Response | UI Elements | Notes |
|--------|-------|--------|-----------------|------------|-------|
| 1 | User | Selects existing pattern group | System displays pattern details | Pattern detail panel with edit button | Shows current patterns and usage |
| 2 | User | Selects "Edit Pattern Group" | System opens pattern editor with current patterns | Pattern editor with pre-filled values | Maintains original structure |
| 3 | User | Modifies patterns | System validates changes | Pattern input with syntax highlighting | Warns if changes might affect existing backups |
| 4 | User | Tests updated patterns | System shows matching results | Pattern test tool with sample results | Verifies changes have expected effect |
| 5 | User | Saves changes | System updates pattern group | Save button, success notification | Updates pattern group in all associated backups |

## Step-by-Step Flow: Deleting a Pattern Group

| Step # | Actor | Action | System Response | UI Elements | Notes |
|--------|-------|--------|-----------------|------------|-------|
| 1 | User | Selects pattern group | System displays pattern details | Pattern detail panel with delete button | Shows usage in existing backups |
| 2 | User | Selects "Delete Pattern Group" | System checks for dependencies | Confirmation dialog with dependency list | Warns if pattern group is in use |
| 3 | User | Confirms deletion | System removes pattern group | Progress indicator | Option to update dependent backups |
| 4 | System | Completes deletion | System updates pattern group list | Updated list, confirmation message | Pattern group no longer available |

## Exit Points

Users exit this flow when:
- Returning to the pattern list after completing operations
- Navigating back to the settings menu
- Returning to backup configuration after pattern management

## Error Scenarios

| Error Scenario | Trigger | System Response | User Recovery Action |
|----------------|---------|-----------------|---------------------|
| Invalid Pattern Syntax | Malformed pattern expression | Specific error with syntax guidance | Correct pattern syntax following guidance |
| Conflicting Patterns | Inclusion and exclusion patterns conflict | Warning with explanation of conflict | Adjust patterns to resolve conflict |
| Dependency Conflict | Attempting to delete pattern in use | Warning with list of dependent backups | Update dependent backups or cancel deletion |
| Duplicate Pattern | Adding already existing pattern | Notification of duplicate | Remove duplicate or continue if intentional |
| Empty Pattern Group | Saving group with no patterns | Warning about empty group | Add at least one pattern or cancel |

## UI Components

### Pattern Group List
- **Group Cards**: Visual representation of each pattern group
- **Usage Indicators**: Shows how many backups use each group
- **Quick Actions**: Buttons for edit, duplicate, delete
- **Search/Filter**: Tools to find specific pattern groups
- **Sorting Options**: Sort by name, usage, date created

### Pattern Editor
- **Name Field**: Input for pattern group name with validation
- **Inclusion Pattern Section**: Area for adding inclusion patterns
- **Exclusion Pattern Section**: Area for adding exclusion patterns
- **Syntax Highlighting**: Visual cues for pattern syntax elements
- **Auto-completion**: Suggestions for common pattern elements

### Pattern Tester
- **Sample Path Input**: Field to enter test file paths
- **Test Button**: Runs the current patterns against sample paths
- **Result Display**: Shows whether paths match or are excluded
- **Explanation**: Details why a path matched or was excluded
- **Common Samples**: Pre-populated examples of typical paths

### Pattern Templates
- **Template Library**: Collection of common pattern sets
- **Category Filters**: Organize templates by purpose
- **Preview**: See template contents before applying
- **Customization**: Modify templates before saving
- **Import/Export**: Share templates between systems

### Dependency Viewer
- **Usage List**: Shows backups using selected pattern group
- **Impact Analysis**: Explains effect of changes on backups
- **Batch Update**: Apply changes to all dependent backups
- **Selective Update**: Choose which backups to update
- **Conflict Resolution**: Tools to resolve pattern conflicts

## Design Considerations

### For Everyday Users (Sarah)
- Simplified pattern creation with visual examples
- Pre-configured templates for common scenarios
- Plain-language explanations of pattern behavior
- Interactive testing with clear results

### For Power Users (Michael)
- Full support for advanced pattern syntax
- Batch operations for managing multiple pattern groups
- Detailed pattern analysis and optimization tools
- Import/export capabilities for sharing patterns

### For Business Users (Elena)
- Business-focused pattern templates (accounting files, client data)
- Compliance-aware patterns for regulated industries
- Team sharing of standardized pattern groups
- Audit trail of pattern changes

## Related Flows

- [Backup Management Flow](backup-management-flow.md) - Uses pattern groups for file selection
- [Initial Setup Flow](initial-setup-flow.md) - May include pattern selection during setup
- [Settings Management Flow](settings-management-flow.md) - Provides access to pattern management