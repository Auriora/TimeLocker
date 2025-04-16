import pytest
from DataProtector.utils.command_builder import CommandBuilder, CommandDefinition, CommandParameter, ParameterStyle

class TestCommandShortForm:
    @pytest.fixture
    def cmd_def(self):
        """Fixture providing a command definition with short form parameters"""
        return CommandDefinition(
            "test-cmd",
            parameters={
                "help": CommandParameter(
                    name="help",
                    style=ParameterStyle.SEPARATE,
                    value_required=False,
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

    @pytest.fixture
    def builder(self, cmd_def):
        """Fixture providing a command builder instance"""
        return CommandBuilder(cmd_def)

    def test_short_form_parameters(self, builder):
        """Test building command with short form parameters
        
        Verifies that when use_short_form=True:
        - Long parameter names are converted to their short forms
        - Parameter styles are adjusted according to short_style
        """
        result = (builder
                .param("help")
                .param("output", "file.txt")
                .build(use_short_form=True))
        assert result == ["test-cmd", "-h", "-o", "file.txt"]

    def test_long_form_parameters(self, builder):
        """Test building command with long form parameters
        
        Verifies that when use_short_form=False:
        - Long parameter names are used
        - Original parameter styles are preserved
        """
        result = (builder
                .param("help")
                .param("output", "file.txt")
                .build(use_short_form=False))
        assert result == ["test-cmd", "--help", "--output=file.txt"]