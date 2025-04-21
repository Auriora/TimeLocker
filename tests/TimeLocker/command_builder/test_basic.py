"""
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
"""

import pytest

from TimeLocker.command_builder import CommandBuilder, CommandDefinition, CommandParameter, ParameterStyle


@pytest.fixture
def cmd_def():
    """Basic command definition for testing"""
    return CommandDefinition(
        "test-cmd",
        parameters={
            "verbose": CommandParameter(name="verbose", style=ParameterStyle.DOUBLE_DASH),
            "output": CommandParameter(name="output", style=ParameterStyle.SEPARATE),
            "format": CommandParameter(name="format", style=ParameterStyle.SEPARATE),
        },
        default_param_style=ParameterStyle.JOINED,
        subcommands={
            "backup": CommandDefinition(
                "backup",
                parameters={
                    "source": CommandParameter(name="source", style=ParameterStyle.SEPARATE),
                    "verbose": CommandParameter(name="verbose", style=ParameterStyle.DOUBLE_DASH)
                }
            )
        }
    )

@pytest.fixture
def builder(cmd_def):
    """Command builder instance for testing"""
    return CommandBuilder(cmd_def)

class TestBasicCommandBuilding:
    def test_basic_command(self, builder):
        """Test basic command without parameters"""
        result = builder.build()
        assert result == ["test-cmd"]

    def test_with_parameter_no_value(self, builder):
        """Test parameter without value (flag-style)"""
        result = builder.param("verbose").build()
        assert result == ["test-cmd", "--verbose"]

    def test_with_parameter_with_value(self, builder):
        """Test parameter with value"""
        result = builder.param("output", "file.txt").build()
        assert result == ["test-cmd", "--output", "file.txt"]

    def test_parameter_chaining(self, builder):
        """Test chaining multiple parameters"""
        result = (builder
                .param("verbose")
                .param("output", "file.txt")
                .param("format", "json")
                .build())
        assert result == ["test-cmd", "--verbose", "--output", "file.txt", "--format", "json"]

class TestSubcommands:
    def test_subcommand(self, builder):
        """Test adding a subcommand"""
        result = builder.command("backup").build()
        assert result == ["test-cmd", "backup"]

    def test_subcommand_with_parameters(self, builder):
        """Test subcommand with parameters"""
        result = (builder
                .command("backup")
                .param("source", "/path")
                .param("verbose")
                .build())
        assert result == ["test-cmd", "backup", "--source", "/path", "--verbose"]

class TestBuilderState:
    def test_reset(self, builder):
        """Test resetting the builder"""
        builder.param("verbose")
        builder.clear()
        result = builder.build()
        assert result == ["test-cmd"]
