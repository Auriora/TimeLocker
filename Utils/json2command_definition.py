import json
from pathlib import Path
from typing import List, Dict, Any

from utils.command_builder import CommandParameter, ParameterStyle, CommandDefinition

# Get the project root directory (two levels up from this script)
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / 'docs'


def convert_json_to_command_definition(json_data: List[dict]) -> CommandDefinition:
    """Convert the JSON data to a CommandDefinition structure."""
    main_command = find_main_command(json_data)
    process_subcommands(json_data, main_command)
    return main_command

def find_main_command(json_data: List[dict]) -> CommandDefinition:
    """Find and create the main command definition."""
    for command_data in json_data:
        if 'SYNOPSIS' in command_data and command_data['SYNOPSIS']['command'] is None:
            return create_command_definition(command_data, is_main=True)

    return CommandDefinition(
        name="restic",
        default_param_style=ParameterStyle.DOUBLE_DASH
    )

def create_command_definition(command_data: dict, is_main: bool = False) -> CommandDefinition:
    """Create a CommandDefinition from command data."""
    name = command_data['SYNOPSIS']['executable'] if is_main else command_data['SYNOPSIS']['command']
    parameters = create_parameters(command_data.get('OPTIONS', []))
    synopsis_params = extract_synopsis_params(command_data['SYNOPSIS'])

    return CommandDefinition(
        name=name,
        parameters=parameters,
        default_param_style=ParameterStyle.DOUBLE_DASH,
        synopsis_params=synopsis_params
    )

def create_parameters(options: List[dict]) -> Dict[str, Any]:
    """Create parameters dictionary from options."""
    return {
        option['long_flag'].replace('--', '') if option['long_flag'] else option['short_flag'].replace('-', ''):
        convert_option_to_parameter(option)
        for option in options
    }

def extract_synopsis_params(synopsis: dict) -> List[str]:
    """Extract synopsis parameters."""
    return [
        param for param in synopsis.get('parameters', [])
        if not param.startswith('[flags]')
    ]

def process_subcommands(json_data: List[dict], main_command: CommandDefinition) -> None:
    """Process subcommands and add them to the main command."""
    for command_data in json_data:
        if 'SYNOPSIS' in command_data and command_data['SYNOPSIS']['command'] is not None:
            subcommand = create_command_definition(command_data)
            main_command.subcommands[subcommand.name] = subcommand

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

    result.append(f"{indent_str_inner}default_param_style={format_parameter_style(cmd_def.default_param_style)}\n")
    result.append(f"{indent_str})")
    return "".join(result)

def main():
    # Read the JSON file from the docs directory
    json_file_path = DOCS_DIR / 'restic_commands.json'
    if not json_file_path.exists():
        raise FileNotFoundError(f"Could not find restic_commands.json in {json_file_path}")

    with json_file_path.open('r') as f:
        json_data = json.load(f)

    # Convert to CommandDefinition
    command_def = convert_json_to_command_definition(json_data)

    # Format and write the output
    formatted_output = (
        "from utils.command_builder import CommandParameter, ParameterStyle, CommandDefinition\n\n"
        f"restic_command_def = {format_command_definition(command_def)}\n"
    )

    # Write to a Python file in the same directory as the input file
    output_file = DOCS_DIR / 'restic_command_definition.py'
    with output_file.open('w') as f:
        f.write(formatted_output)
    print(f"Command definition written to {output_file}")

if __name__ == "__main__":
    main()





