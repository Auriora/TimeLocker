# CommandBuilder Basic Test Suite
Tags: command-builder, basic
Meta: component = TimeLocker, module = command_builder

## S1 Basic Command Building
* C1 Test basic command without parameters
Tags: command
    * Create a CommandDefinition with parameters and subcommands
    * Create a CommandBuilder with the definition
    * Call build() without adding any parameters
    * Verify the result is a list containing only the command name
* C2 Test parameter without value (flag-style)
Tags: parameter, flag
    * Create a CommandDefinition with parameters including a flag parameter
    * Create a CommandBuilder with the definition
    * Add a flag parameter using param()
    * Call build()
    * Verify the result contains the command name and the flag parameter
* C3 Test parameter with value
Tags: parameter, value
    * Create a CommandDefinition with parameters including a value parameter
    * Create a CommandBuilder with the definition
    * Add a parameter with a value using param()
    * Call build()
    * Verify the result contains the command name, parameter name, and parameter value
* C4 Test chaining multiple parameters
Tags: parameter, chaining
    * Create a CommandDefinition with multiple parameters
    * Create a CommandBuilder with the definition
    * Chain multiple param() calls to add parameters
    * Call build()
    * Verify the result contains the command name and all parameters in the correct order

## S2 Subcommand Handling
* C1 Test adding a subcommand
Tags: subcommand
    * Create a CommandDefinition with subcommands
    * Create a CommandBuilder with the definition
    * Add a subcommand using command()
    * Call build()
    * Verify the result contains the command name and subcommand name
* C2 Test subcommand with parameters
Tags: subcommand, parameter
    * Create a CommandDefinition with subcommands that have parameters
    * Create a CommandBuilder with the definition
    * Add a subcommand using command()
    * Add parameters to the subcommand
    * Call build()
    * Verify the result contains the command name, subcommand name, and all parameters

## S3 Builder State Management
* C1 Test resetting the builder
Tags: state, reset
    * Create a CommandDefinition with parameters
    * Create a CommandBuilder with the definition
    * Add a parameter
    * Call clear() to reset the builder
    * Call build()
    * Verify the result contains only the command name, with no parameters