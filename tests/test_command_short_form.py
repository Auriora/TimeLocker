import unittest
from src.utils.command_builder import CommandBuilder, CommandDefinition, CommandParameter, ParameterStyle

class TestCommandShortForm(unittest.TestCase):
    def setUp(self):
        self.cmd_def = CommandDefinition(
            "test-cmd",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.SEPARATE,
                    short_name="h",
                    short_style=ParameterStyle.SINGLE_DASH
                ),
                "output": CommandParameter(
                    name="output",
                    style=ParameterStyle.JOINED,
                    short_name="o",
                    short_style=ParameterStyle.SEPARATE
                )
            }
        )
        self.builder = CommandBuilder(self.cmd_def)

    def test_short_form_parameters(self):
        """Test building command with short form parameters"""
        result = (self.builder
                 .with_parameter("help")
                 .with_parameter("output", "file.txt")
                 .build(use_short_form=True))
        self.assertEqual(result, ["test-cmd", "-h", "-o", "file.txt"])

    def test_long_form_parameters(self):
        """Test building command with long form parameters"""
        result = (self.builder
                 .with_parameter("help")
                 .with_parameter("output", "file.txt")
                 .build(use_short_form=False))
        self.assertEqual(result, ["test-cmd", "--help", "--output=file.txt"])

    def test_mixed_form_parameters(self):
        """Test building command with a mix of short and long form parameters"""
        result = (self.builder
                 .with_parameter("help", use_short_form=True)
                 .with_parameter("output", "file.txt", use_short_form=False)
                 .build())
        self.assertEqual(result, ["test-cmd", "-h", "--output=file.txt"])