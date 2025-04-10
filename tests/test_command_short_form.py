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
                 .param("help")
                 .param("output", "file.txt")
                 .build(use_short_form=True))
        self.assertEqual(["test-cmd", "-h", "-o", "file.txt"], result)

    def test_long_form_parameters(self):
        """Test building command with long form parameters"""
        result = (self.builder
                 .param("help")
                 .param("output", "file.txt")
                 .build(use_short_form=False))
        self.assertEqual(["test-cmd", "--help", "--output=file.txt"], result)
