import pytest
from src.utils.command_builder import CommandBuilder, CommandDefinition, CommandParameter, ParameterStyle

@pytest.fixture
def cmd_def():
    return CommandDefinition(
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

@pytest.fixture
def builder(cmd_def):
    return CommandBuilder(cmd_def)

def test_short_form_parameters(builder):
    """Test building command with short form parameters"""
    result = (builder
             .param("help")
             .param("output", "file.txt")
             .build(use_short_form=True))
    assert result == ["test-cmd", "-h", "-o", "file.txt"]

def test_long_form_parameters(builder):
    """Test building command with long form parameters"""
    result = (builder
             .param("help")
             .param("output", "file.txt")
             .build(use_short_form=False))
    assert result == ["test-cmd", "--help", "--output=file.txt"]