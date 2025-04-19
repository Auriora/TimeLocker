# CommandBuilder Short Form Test Suite
Tags: command-builder, short-form
Meta: component = TimeLocker, module = command_builder

## S1 Short Form Parameters
* C1 Test building command with short form parameters
Tags: short-form
    * Create a CommandDefinition with parameters that have short_name and short_style defined
    * Create a CommandBuilder with the definition
    * Add parameters using their long names
    * Call build() with use_short_form=True
    * Verify the result contains the short form parameter names and styles
* C2 Test building command with long form parameters
Tags: long-form
    * Create a CommandDefinition with parameters that have short_name and short_style defined
    * Create a CommandBuilder with the definition
    * Add parameters using their long names
    * Call build() with use_short_form=False (or omit the parameter)
    * Verify the result contains the long form parameter names and original styles