import pytest
from utils.command_builder import ParameterStyle

class TestParameterStyleEquality:
    def test_equality_with_same_style(self):
        """Test equality between two ParameterStyle instances with same value."""
        style1 = ParameterStyle.SEPARATE
        style2 = ParameterStyle.SEPARATE
        assert style1 == style2
        assert not (style1 != style2)

    def test_equality_with_string(self):
        """Test equality between ParameterStyle and string."""
        style = ParameterStyle.JOINED
        assert style == "joined"
        assert style == "JOINED"  # Case insensitive
        assert not (style != "joined")
        assert not (style != "JOINED")

    def test_inequality_with_different_style(self):
        """Test inequality between different ParameterStyle values."""
        style1 = ParameterStyle.SEPARATE
        style2 = ParameterStyle.JOINED
        assert style1 != style2
        assert not (style1 == style2)

class TestParameterStyleComparisons:
    def test_inequality_with_none(self):
        """Test inequality with None value."""
        style = ParameterStyle.SEPARATE
        assert style != None
        assert not (style == None)

    def test_inequality_with_other_types(self):
        """Test inequality with other types."""
        style = ParameterStyle.SEPARATE
        assert style != 42
        assert style != True
        assert not (style == 42)
        assert not (style == True)