            # if param.prefix:
            #     result.append(f"{indent_str_inner}        prefix=\"{param.prefix}\",\n")
import json
from typing import List

from utils.command_builder import CommandParameter, ParameterStyle, CommandDefinition

def convert_json_to_command_definition(json_data: List[dict]) -> CommandDefinition:
    """Convert the JSON data to a CommandDefinition structure."""
    main_command = CommandDefinition(
        name="restic",
        default_param_style=ParameterStyle.DOUBLE_DASH
    )

    # First pass: find common parameters (where command is null)
    for command_data in json_data:
        if 'SYNOPSIS' in command_data and command_data['SYNOPSIS']['command'] is None:
            if 'OPTIONS' in command_data:
                main_command.parameters = {
                    option['long_flag'].replace('--', '') if option['long_flag'] else option['short_flag'].replace('-', ''):
                    convert_option_to_parameter(option)
                    for option in command_data['OPTIONS']
                }
            break

    # Second pass: process subcommands
    for command_data in json_data:
        if 'SYNOPSIS' in command_data:
            command_name = command_data['SYNOPSIS']['command']
            if command_name is None:
                continue  # Skip the main command definition

            # Convert options to parameters dictionary
            parameters = {}
            if 'OPTIONS' in command_data:
                for option in command_data['OPTIONS']:
                    param = convert_option_to_parameter(option)
                    parameters[param.name] = param

            # Create the command definition
            command_def = CommandDefinition(
                name=command_name,
                parameters=parameters,
                default_param_style=ParameterStyle.DOUBLE_DASH
            )

            # Add to main command's subcommands
            main_command.subcommands[command_name] = command_def

    return main_command

def determine_parameter_style(option: dict) -> ParameterStyle:
    """Determine the parameter style based on the option configuration."""
    if option['short_flag']:
        return ParameterStyle.SINGLE_DASH
    elif option['long_flag']:
        return ParameterStyle.DOUBLE_DASH
    return ParameterStyle.SEPARATE

def convert_option_to_parameter(option: dict) -> CommandParameter:
    """Convert a JSON option object to a CommandParameter."""
    # Extract the parameter name from the long flag
    if option['long_flag']:
        name = option['long_flag'].replace('--', '')
        style = ParameterStyle.DOUBLE_DASH
    else:
        name = None
        style = None

    if option['short_flag']:
        short_name = option['short_flag'].replace('-', '')
        short_style = ParameterStyle.SINGLE_DASH
    else:
        short_name = None
        short_style = None

    # Determine if a value is required
    value_required = option['value_type'] != 'string' or option['default'] != 'false'

    return CommandParameter(
        name=name,
        style=style,
        short_name=short_name,
        short_style=short_style,
        required=False,  # Default to False as most CLI options are optional
        value_required=value_required,
        description=option['description'] or ""
    )

# [Previous imports and class definitions remain the same]

def format_parameter_style(style: ParameterStyle) -> str:
    """Convert ParameterStyle enum to string representation."""
    return f"ParameterStyle.{style.name}"

def format_command_definition(cmd_def: CommandDefinition, indent: int = 0) -> str:
    """Format a CommandDefinition as a Python code string."""
    indent_str = " " * indent
    result = ["CommandDefinition(\n"]
    indent_str_inner = " " * (indent + 4)

    result.append(f"{indent_str_inner}name=\"{cmd_def.name}\",\n")

    # Format parameters
    if cmd_def.parameters:
        result.append(f"{indent_str_inner}parameters={{\n")
        for param_name, param in cmd_def.parameters.items():
            result.append(f"{indent_str_inner}    \"{param_name}\": CommandParameter(\n")
            if param.name:
                result.append(f"{indent_str_inner}        name=\"{param.name}\",\n")
                result.append(f"{indent_str_inner}        style={format_parameter_style(param.style)},\n")
            if param.short_name:
                result.append(f"{indent_str_inner}        short_name=\"{param.short_name}\",\n")
                result.append(f"{indent_str_inner}        short_style={format_parameter_style(param.short_style)},\n")
            if param.required:
                result.append(f"{indent_str_inner}        required={param.required},\n")
            if param.value_required:
                result.append(f"{indent_str_inner}        value_required={param.value_required},\n")
            if param.description:
                result.append(f"{indent_str_inner}        description={repr(param.description)},\n")
            result.append(f"{indent_str_inner}    ),\n")
        result.append(f"{indent_str_inner}}},\n")

    # Format subcommands
    if cmd_def.subcommands:
        result.append(f"{indent_str_inner}subcommands={{\n")
        for subcmd_name, subcmd in cmd_def.subcommands.items():
            result.append(f"{indent_str_inner}    \"{subcmd_name}\": {format_command_definition(subcmd, indent + 8)},\n")
        result.append(f"{indent_str_inner}}},\n")

    result.append(f"{indent_str_inner}default_param_style=ParameterStyle.SEPARATE\n")
    result.append(f"{indent_str})")
    return "".join(result)

def main():
    # Read the JSON file
    with open('restic_commands.json', 'r') as f:
        json_data = json.load(f)

    # Convert to CommandDefinition
    command_def = convert_json_to_command_definition(json_data)

    # Format and write the output
    formatted_output = (
        "from utils.command_builder import CommandParameter, ParameterStyle, CommandDefinition\n\n"
        f"restic_command = {format_command_definition(command_def)}\n"
    )

    # Write to a Python file
    with open('restic_commands_definition.py', 'w') as f:
        f.write(formatted_output)

if __name__ == "__main__":
    main()
