import pytest
from DataProtector.utils.command_builder import CommandBuilder, CommandDefinition, ParameterStyle, CommandParameter

class TestSynopsisParameters:
    @pytest.fixture
    def cmd_def(self):
        """Command definition with synopsis parameters"""
        return CommandDefinition(
            "test-cmd",
            parameters={
                "verbose": CommandParameter(name="verbose", style=ParameterStyle.DOUBLE_DASH)
            },
            synopsis_params=["snapshotID", "[dir...]"]
        )

    @pytest.fixture
    def builder(self, cmd_def):
        """Command builder instance"""
        return CommandBuilder(cmd_def)

    def test_synopsis_parameters(self, builder):
        """Test handling of synopsis parameters"""
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