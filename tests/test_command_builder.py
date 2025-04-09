import unittest
from src.utils.command_builder import CommandBuilder, CommandDefinition, ParameterStyle

class TestCommandBuilder(unittest.TestCase):
    def setUp(self):
        # Basic command definition for testing
        self.cmd_def = CommandDefinition(
            "test-cmd",
            parameters={"description": "A test command"}, default_param_style=ParameterStyle.JOINED,
            subcommands={"backup": CommandDefinition(
                "backup"
                # parameters={"description": "Backup command"}
            )}
        )
        self.builder = CommandBuilder(self.cmd_def)
    
    def test_basic_command(self):
        """Test basic command without parameters"""
        result = self.builder.build()
        self.assertEqual(result, ["test-cmd"])
    
    def test_with_parameter_no_value(self):
        """Test parameter without value (flag-style)"""
        result = self.builder.with_parameter("verbose", style=ParameterStyle.DOUBLE_DASH).build()
        self.assertEqual(result, ["test-cmd", "--verbose"])
    
    def test_with_parameter_with_value(self):
        """Test parameter with value"""
        result = self.builder.with_parameter("output", "file.txt", style=ParameterStyle.SEPARATE).build()
        self.assertEqual(result, ["test-cmd", "--output", "file.txt"])
    
    def test_parameter_chaining(self):
        """Test chaining multiple parameters"""
        result = (self.builder
                 .with_parameter("verbose", style=ParameterStyle.DOUBLE_DASH)
                 .with_parameter("output", "file.txt", style=ParameterStyle.SEPARATE)
                 .with_parameter("format", "json", style=ParameterStyle.SEPARATE)
                 .build())
        self.assertEqual(
            result,
            ["test-cmd", "--verbose", "--output", "file.txt", "--format", "json"]
        )
    
    def test_subcommand(self):
        """Test adding a subcommand"""
        result = self.builder.with_subcommand("backup").build()
        self.assertEqual(result, ["test-cmd", "backup"])
    
    def test_subcommand_with_parameters(self):
        """Test subcommand with parameters"""
        result = (self.builder
                 .with_subcommand("backup")
                 .with_parameter("source", "/path")
                 .with_parameter("verbose", style=ParameterStyle.DOUBLE_DASH)
                 .build())
        self.assertEqual(
            result,
            ["test-cmd", "backup", "--source", "/path", "--verbose"]
        )
    
    def test_reset(self):
        """Test resetting the builder"""
        self.builder.with_parameter("verbose", style=ParameterStyle.DOUBLE_DASH)
        self.builder.reset()
        result = self.builder.build()
        self.assertEqual(result, ["test-cmd"])
    
    def test_different_parameter_styles(self):
        """Test different parameter styles"""
        cmd_def = CommandDefinition(
            "test-cmd",
            parameters={"description": "Test command with different styles"},
            default_param_style=ParameterStyle.SINGLE_DASH
        )
        builder = CommandBuilder(cmd_def)
        
        result = (builder
                 .with_parameter("v")
                 .with_parameter("output", "file.txt")
                 .build())
        self.assertEqual(result, ["test-cmd", "-v", "-output", "file.txt"])
    
    def test_list_parameters(self):
        """Test parameters with list values"""
        result = (self.builder
                 .with_parameter("tags", ["tag1", "tag2", "tag3"], style=ParameterStyle.POSITIONAL)
                 .build())
        self.assertEqual(
            result,
            ["test-cmd", "tags", "tag1", "tags", "tag2", "tags", "tag3"]
        )

if __name__ == '__main__':
    unittest.main()