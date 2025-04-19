# CommandBuilder Parameters Test Suite
Tags: command-builder, parameters
Meta: component = TimeLocker, module = command_builder

## S1 Parameter Styles
* C1 Test different parameter styles
Tags: style
    * Create a CommandDefinition with parameters using different styles (e.g., SINGLE_DASH)
    * Create a CommandBuilder with the definition
    * Add parameters with different styles
    * Call build()
    * Verify the result contains the parameters with the correct styles
* C2 Test parameter style equality
Tags: style, equality
    * Create two ParameterStyle instances with the same value
    * Verify they are equal using == operator
    * Verify they are not unequal using != operator
* C3 Test parameter style string comparison
Tags: style, comparison
    * Create a ParameterStyle instance
    * Compare it with equivalent string values (case insensitive)
    * Verify they are equal using == operator
    * Verify they are not unequal using != operator
* C4 Test parameter style inequality
Tags: style, inequality
    * Create two ParameterStyle instances with different values
    * Verify they are not equal using != operator
    * Verify they are not equal using == operator
* C5 Test parameter style None comparison
Tags: style, comparison
    * Create a ParameterStyle instance
    * Compare it with None
    * Verify they are not equal using != operator
    * Verify they are not equal using == operator
* C6 Test parameter style other types comparison
Tags: style, comparison
    * Create a ParameterStyle instance
    * Compare it with other types (e.g., integer, boolean)
    * Verify they are not equal using != operator
    * Verify they are not equal using == operator

## S2 List Parameters
* C1 Test list positional parameters
Tags: list, positional
    * Create a CommandDefinition with a positional parameter
    * Create a CommandBuilder with the definition
    * Add a parameter with a list value
    * Call build()
    * Verify the result contains the parameter name repeated for each list item
* C2 Test list separate parameters
Tags: list, separate
    * Create a CommandDefinition with a separate-style parameter
    * Create a CommandBuilder with the definition
    * Add a parameter with a list value
    * Call build()
    * Verify the result contains the parameter name repeated for each list item
* C3 Test list joined parameters
Tags: list, joined
    * Create a CommandDefinition with a joined-style parameter
    * Create a CommandBuilder with the definition
    * Add a parameter with a list value
    * Call build()
    * Verify the result contains the parameter name joined with each list item