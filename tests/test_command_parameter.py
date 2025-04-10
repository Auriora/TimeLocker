import unittest
from src.utils.command_builder import CommandParameter, ParameterStyle

class TestCommandParameter(unittest.TestCase):
    def test_short_and_long_forms(self):
        """Test parameters with both short and long forms."""
        param = CommandParameter(
            name="help",
            style=ParameterStyle.SEPARATE,
            short_name="h",
            short_style=ParameterStyle.SINGLE_DASH
        )
        
        # Test long form
        self.assertEqual(param.format_param_name(use_short_form=False), "--help")
        
        # Test short form
        self.assertEqual(param.format_param_name(use_short_form=True), "-h")

    def test_different_styles_for_forms(self):
        """Test parameters with different styles for short/long forms."""
        param = CommandParameter(
            name="output",
            style=ParameterStyle.JOINED,  # --output=value
            short_name="o",
            short_style=ParameterStyle.SEPARATE  # -o value
        )
        
        # Long form should use JOINED style
        self.assertEqual(param.format_param_name(use_short_form=False), "--output")
        
        # Short form should use SEPARATE style
        self.assertEqual(param.format_param_name(use_short_form=True), "-o")

    def test_short_form_default_style(self):
        """Test short form defaults to SINGLE_DASH when no style specified."""
        param = CommandParameter(
            name="verbose",
            style=ParameterStyle.DOUBLE_DASH,
            short_name="v"  # No short_style specified
        )
        
        # Test that short form defaults to SINGLE_DASH
        self.assertEqual(param.format_param_name(use_short_form=True), "-v")
        self.assertEqual(param.format_param_name(use_short_form=False), "--verbose")