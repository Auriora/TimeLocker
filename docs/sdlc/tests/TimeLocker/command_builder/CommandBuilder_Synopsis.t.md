# CommandBuilder Synopsis Test Suite
Tags: command-builder, synopsis
Meta: component = TimeLocker, module = command_builder

## S1 Synopsis Parameters
* C1 Test handling of required synopsis parameters
Tags: synopsis, required
    * Create a CommandDefinition with synopsis_params including a required parameter
    * Create a CommandBuilder with the definition
    * Call build() with synopsis_values containing the required parameter
    * Verify the result contains the command name followed by the synopsis parameter value
* C2 Test handling of optional synopsis parameters
Tags: synopsis, optional
    * Create a CommandDefinition with synopsis_params including required and optional parameters
    * Create a CommandBuilder with the definition
    * Call build() with synopsis_values containing both required and optional parameters
    * Verify the result contains the command name followed by all synopsis parameter values
* C3 Test combining flags and synopsis parameters
Tags: synopsis, flags
    * Create a CommandDefinition with parameters and synopsis_params
    * Create a CommandBuilder with the definition
    * Add a flag parameter
    * Call build() with synopsis_values
    * Verify the result contains the command name, flag, and synopsis parameter values
* C4 Test missing required synopsis parameter
Tags: synopsis, required, validation
    * Create a CommandDefinition with synopsis_params including a required parameter
    * Create a CommandBuilder with the definition
    * Call build() with empty synopsis_values
    * Verify a ValueError is raised

## S2 Synopsis with Subcommands
* C1 Test synopsis parameters with subcommands
Tags: synopsis, subcommand
    * Create a CommandDefinition with a subcommand that has synopsis_params
    * Create a CommandBuilder with the definition
    * Add the subcommand
    * Add parameters to the subcommand
    * Call build() with synopsis_values
    * Verify the result contains the command name, subcommand, parameters, and synopsis parameter values