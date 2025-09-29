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


class TestParameterStyles:
    @pytest.mark.unit
    def test_different_parameter_styles(self):
        """Test different parameter styles"""
        cmd_def = CommandDefinition(
            "test-cmd",
            parameters={
                "v": CommandParameter(name="v", style=ParameterStyle.SINGLE_DASH),
                "output": CommandParameter(name="output", style=ParameterStyle.SINGLE_DASH)
            },
            default_param_style=ParameterStyle.SINGLE_DASH
        )
        builder = CommandBuilder(cmd_def)

        result = (builder
                .param("v")
                .param("output", "file.txt")
                .build())
        assert result == ["test-cmd", "-v", "-output", "file.txt"]

    @pytest.mark.unit
    def test_parameter_style_equality(self):
        """Test equality between two ParameterStyle instances with same value."""
        style1 = ParameterStyle.SEPARATE
        style2 = ParameterStyle.SEPARATE
        assert style1 == style2
        assert not (style1 != style2)

    @pytest.mark.unit
    def test_parameter_style_string_comparison(self):
        """Test equality between ParameterStyle and string."""
        style = ParameterStyle.JOINED
        assert style == "joined"
        assert style == "JOINED"  # Case insensitive
        assert not (style != "joined")
        assert not (style != "JOINED")

    @pytest.mark.unit
    def test_parameter_style_inequality(self):
        """Test inequality between different ParameterStyle values."""
        style1 = ParameterStyle.SEPARATE
        style2 = ParameterStyle.JOINED
        assert style1 != style2
        assert not (style1 == style2)

    @pytest.mark.unit
    def test_parameter_style_none_comparison(self):
        """Test inequality with None value."""
        style = ParameterStyle.SEPARATE
        assert style != None
        assert not (style == None)

    @pytest.mark.unit
    def test_parameter_style_other_types(self):
        """Test inequality with other types."""
        style = ParameterStyle.SEPARATE
        assert style != 42
        assert style != True
        assert not (style == 42)
        assert not (style == True)

class TestListParameters:
    @pytest.mark.unit
    def test_list_positional_parameters(self):
        """Test parameters with list values"""
        cmd_def = CommandDefinition(
            "test-cmd",
            parameters={
                "tags": CommandParameter(name="tags", style=ParameterStyle.POSITIONAL)
            }
        )
        builder = CommandBuilder(cmd_def)
        result = (builder
                .param("tags", ["tag1", "tag2", "tag3"])
                .build())
        assert result == ["test-cmd", "tags", "tag1", "tags", "tag2", "tags", "tag3"]

    @pytest.mark.unit
    def test_list_separate_parameters(self):
        """Test parameters with list values using separate style"""
        cmd_def = CommandDefinition(
            "test-cmd",
            parameters={
                "tags": CommandParameter(name="tags", style=ParameterStyle.SEPARATE)
            }
        )
        builder = CommandBuilder(cmd_def)
        result = (builder
                .param("tags", ["tag1", "tag2", "tag3"])
                .build())
        assert result == ["test-cmd", "--tags", "tag1", "--tags", "tag2", "--tags", "tag3"]

    @pytest.mark.unit
    def test_list_joined_parameters(self):
        """Test parameters with list values using joined style"""
        cmd_def = CommandDefinition(
            "test-cmd",
            parameters={
                "tags": CommandParameter(name="tags", style=ParameterStyle.JOINED)
            }
        )
        builder = CommandBuilder(cmd_def)
        result = (builder
                .param("tags", ["tag1", "tag2", "tag3"])
                .build())
        assert result == ["test-cmd", "--tags=tag1", "--tags=tag2", "--tags=tag3"]
