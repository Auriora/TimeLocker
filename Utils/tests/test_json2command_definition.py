import unittest
from Utils.json2command_definition import convert_json_to_command_definition
from src.utils.command_builder import ParameterStyle

class TestJson2CommandDefinition(unittest.TestCase):
    def test_synopsis_handling(self):
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
        self.assertEqual(command_def.name, "restic")
        self.assertEqual(command_def.default_param_style, ParameterStyle.DOUBLE_DASH)
        self.assertEqual(command_def.synopsis_params, ["command", "[args]"])

        # Verify subcommand
        self.assertIn("backup", command_def.subcommands)
        backup_cmd = command_def.subcommands["backup"]
        self.assertEqual(backup_cmd.name, "backup")
        self.assertEqual(backup_cmd.synopsis_params, ["[FILE/DIR]", "..."])

    def test_no_main_command_synopsis(self):
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
        self.assertEqual(command_def.name, "restic")
        self.assertEqual(command_def.default_param_style, ParameterStyle.DOUBLE_DASH)

if __name__ == '__main__':
    unittest.main()