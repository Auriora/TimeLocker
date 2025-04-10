import unittest
from src.utils.command_builder import CommandBuilder, CommandDefinition, ParameterStyle, CommandParameter


class TestCommandBuilder(unittest.TestCase):
    def setUp(self):
        # Basic command definition for testing
        # Define complete command structure with all parameters upfront
        self.cmd_def = CommandDefinition(
            "test-cmd",
            parameters={
                "verbose": CommandParameter(name="verbose", style=ParameterStyle.DOUBLE_DASH),
                "output": CommandParameter(name="output", style=ParameterStyle.SEPARATE),
                "format": CommandParameter(name="format", style=ParameterStyle.SEPARATE),
                "tags": CommandParameter(name="tags", style=ParameterStyle.SEPARATE),
                "v": CommandParameter(name="v", style=ParameterStyle.SINGLE_DASH)
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
        self.builder = CommandBuilder(self.cmd_def)
    
    def test_basic_command(self):
        """Test basic command without parameters"""
        result = self.builder.build()
        self.assertEqual(result, ["test-cmd"])
    
    def test_with_parameter_no_value(self):
        """Test parameter without value (flag-style)"""
        result = self.builder.param("verbose").build()
        self.assertEqual(result, ["test-cmd", "--verbose"])
    
    def test_with_parameter_with_value(self):
        """Test parameter with value"""
        result = self.builder.param("output", "file.txt").build()
        self.assertEqual(result, ["test-cmd", "--output", "file.txt"])
    
    def test_parameter_chaining(self):
        """Test chaining multiple parameters"""
        result = (self.builder
                 .param("verbose")
                 .param("output", "file.txt")
                 .param("format", "json")
                 .build())
        self.assertEqual(
            result,
            ["test-cmd", "--verbose", "--output", "file.txt", "--format", "json"]
        )
    
    def test_subcommand(self):
        """Test adding a subcommand"""
        result = self.builder.command("backup").build()
        self.assertEqual(result, ["test-cmd", "backup"])
    
    def test_subcommand_with_parameters(self):
        """Test subcommand with parameters"""
        result = (self.builder
                 .command("backup")
                 .param("source", "/path")
                 .param("verbose")
                 .build())
        self.assertEqual(
            result,
            ["test-cmd", "backup", "--source", "/path", "--verbose"]
        )
    
    def test_reset(self):
        """Test resetting the builder"""
        self.builder.param("verbose")
        self.builder.clear()
        result = self.builder.build()
        self.assertEqual(result, ["test-cmd"])
    
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
        self.assertEqual(result, ["test-cmd", "-v", "-output", "file.txt"])
    
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
        self.assertEqual(
            result,
            ["test-cmd", "tags", "tag1", "tags", "tag2", "tags", "tag3"]
        )

    def test_list_separate_parameters(self):
        """Test parameters with list values using separate style"""
        result = (self.builder
                 .param("tags", ["tag1", "tag2", "tag3"])
                 .build())
        self.assertEqual(
            result,
            ["test-cmd", "--tags", "tag1", "--tags", "tag2", "--tags", "tag3"]
        )

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
        self.assertEqual(
            result,
            ["test-cmd", "--tags=tag1", "--tags=tag2", "--tags=tag3"]
        )

if __name__ == '__main__':
    unittest.main()
