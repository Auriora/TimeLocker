import pytest
from utils.command_builder import CommandBuilder, CommandDefinition, ParameterStyle, CommandParameter

class TestParameterStyles:
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

class TestListParameters:
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

class TestSynopsisParameters:
    def test_synopsis_parameters(self):
        """Test handling of synopsis parameters"""
        cmd_def = CommandDefinition(
            "test-cmd",
            parameters={
                "verbose": CommandParameter(name="verbose", style=ParameterStyle.DOUBLE_DASH)
            },
            synopsis_params=["snapshotID", "[dir...]"]
        )
        builder = CommandBuilder(cmd_def)
        
        # Test with required synopsis parameter
        result = builder.build(synopsis_values={"snapshotID": "abc123"})
        assert result == ["test-cmd", "abc123"]
        
        # Test with optional synopsis parameter
        result = builder.build(synopsis_values={"snapshotID": "abc123", "dir": "/path/to/dir"})
        assert result == ["test-cmd", "abc123", "/path/to/dir"]
        
        # Test with flags and synopsis parameters
        result = builder.param("verbose").build(synopsis_values={"snapshotID": "abc123"})
        assert result == ["test-cmd", "--verbose", "abc123"]
        
        # Test missing required synopsis parameter
        with pytest.raises(ValueError):
            builder.build(synopsis_values={})

    def test_synopsis_parameters_with_subcommands(self):
        """Test handling of synopsis parameters with subcommands"""
        cmd_def = CommandDefinition(
            "test-cmd",
            subcommands={
                "restore": CommandDefinition(
                    "restore",
                    parameters={
                        "target": CommandParameter(name="target", style=ParameterStyle.DOUBLE_DASH)
                    },
                    synopsis_params=["snapshotID"]
                )
            }
        )
        builder = CommandBuilder(cmd_def)
        
        # Test subcommand with synopsis parameter
        result = (builder
                 .command("restore")
                 .param("target", "/path/to/restore")
                 .build(synopsis_values={"snapshotID": "abc123"}))
        assert result == ["test-cmd", "restore", "--target", "/path/to/restore", "abc123"]