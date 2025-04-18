'''
   Copyright ©  Bruce Cherrington

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program. If not, see <https://www.gnu.org/licenses/>.
'''

from json2command_definition.json2command_definition import convert_json_to_command_definition
from TimeLocker.utils.command_builder import ParameterStyle

def test_synopsis_handling():
    # Test data with SYNOPSIS values
    test_json = [
        {
            "SYNOPSIS": {
                "command": None,
                "executable": "restic",
                "parameters": [
                    "[flags]",
                    "command",
                    "[args]"
                ]
            },
            "OPTIONS": [
                {
                    "long_flag": "--help",
                    "short_flag": "-h",
                    "description": "help for restic",
                    "value_type": "string",
                    "default": "false"
                }
            ]
        },
        {
            "SYNOPSIS": {
                "command": "backup",
                "executable": "restic",
                "parameters": [
                    "[flags]",
                    "[FILE/DIR]",
                    "..."
                ]
            },
            "OPTIONS": [
                {
                    "long_flag": "--help",
                    "short_flag": "-h",
                    "description": "help for backup",
                    "value_type": "string",
                    "default": "false"
                }
            ]
        }
    ]

    # Convert test data
    command_def = convert_json_to_command_definition(test_json)

    # Verify main command
    assert command_def.name == "restic"
    assert command_def.default_param_style == ParameterStyle.DOUBLE_DASH
    assert command_def.synopsis_params == ["command", "[args]"]

    # Verify subcommand
    assert "backup" in command_def.subcommands
    backup_cmd = command_def.subcommands["backup"]
    assert backup_cmd.name == "backup"
    assert backup_cmd.synopsis_params == ["[FILE/DIR]", "..."]

def test_no_main_command_synopsis():
    # Test data without main command SYNOPSIS
    test_json = [
        {
            "SYNOPSIS": {
                "command": "backup",
                "executable": "restic",
                "parameters": [
                    "[flags]",
                    "[FILE/DIR]"
                ]
            }
        }
    ]

    # Convert test data
    command_def = convert_json_to_command_definition(test_json)

    # Verify fallback to default main command
    assert command_def.name == "restic"
    assert command_def.default_param_style == ParameterStyle.DOUBLE_DASH
