# FileSelections Test Suite
Tags: backup, file-selection
Meta: component = TimeLocker, module = backup

## S1 Path Management
* C1 Test adding a path to include list
Tags: path, include
    * Create a FileSelections instance
    * Add a path to the include list
    * Verify the path is in the includes list
    * Verify the path is not in the excludes list
* C2 Test adding a path to exclude list
Tags: path, exclude
    * Create a FileSelections instance
    * Add a path to the exclude list using SelectionType.EXCLUDE
    * Verify the path is in the excludes list
    * Verify the path is not in the includes list
* C3 Test removing a path from selections
Tags: path, remove
    * Create a FileSelections instance
    * Add a path to the include list
    * Remove the path
    * Verify the path is no longer in the includes list

## S2 Pattern Management
* C1 Test adding a single pattern
Tags: pattern, include
    * Create a FileSelections instance
    * Add a pattern (e.g., "*.txt")
    * Verify the pattern is in the include_patterns list
* C2 Test removing a single pattern
Tags: pattern, remove
    * Create a FileSelections instance
    * Add a pattern
    * Remove the pattern
    * Verify the pattern is no longer in the include_patterns list

## S3 Pattern Group Management
* C1 Test adding patterns as exclusions
Tags: pattern-group, exclude
    * Create a FileSelections instance
    * Add a pattern group as exclusions
    * Verify the patterns are in the exclude_patterns list
    * Verify the patterns are not in the include_patterns list
* C2 Test adding a predefined pattern group
Tags: pattern-group, predefined
    * Create a FileSelections instance
    * Add a predefined pattern group (e.g., "office_documents")
    * Verify the expected patterns (e.g., "*.doc", "*.pdf") are in the include_patterns list
* C3 Test adding a custom pattern group
Tags: pattern-group, custom
    * Create a FileSelections instance
    * Create a custom PatternGroup with specific patterns
    * Add the custom pattern group
    * Verify the custom patterns are in the include_patterns list
* C4 Test removing a pattern group
Tags: pattern-group, remove
    * Create a FileSelections instance
    * Add a pattern group
    * Remove the pattern group
    * Verify the patterns from the group are no longer in the include_patterns list

## S4 Validation
* C1 Test that validation requires at least one folder
Tags: validation, folder
    * Create a FileSelections instance
    * Add only a file path (not a folder)
    * Verify that validation raises a ValueError
    * Add a folder path
    * Verify that validation passes