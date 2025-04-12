import pytest
from src.utils.command_builder import CommandBuilder, CommandDefinition, ParameterStyle, CommandParameter


@pytest.fixture
def cmd_def():
    # Basic command definition for testing
    # Define complete command structure with all parameters upfront
    return CommandDefinition(
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

@pytest.fixture
def builder(cmd_def):
    return CommandBuilder(cmd_def)

def test_basic_command(builder):
    """Test basic command without parameters"""
    result = builder.build()
    assert result == ["test-cmd"]

def test_with_parameter_no_value(builder):
    """Test parameter without value (flag-style)"""
    result = builder.param("verbose").build()
    assert result == ["test-cmd", "--verbose"]

def test_with_parameter_with_value(builder):
    """Test parameter with value"""
    result = builder.param("output", "file.txt").build()
    assert result == ["test-cmd", "--output", "file.txt"]

def test_parameter_chaining(builder):
    """Test chaining multiple parameters"""
    result = (builder
             .param("verbose")
             .param("output", "file.txt")
             .param("format", "json")
             .build())
    assert result == ["test-cmd", "--verbose", "--output", "file.txt", "--format", "json"]

def test_subcommand(builder):
    """Test adding a subcommand"""
    result = builder.command("backup").build()
    assert result == ["test-cmd", "backup"]

def test_subcommand_with_parameters(builder):
    """Test subcommand with parameters"""
    result = (builder
             .command("backup")
             .param("source", "/path")
             .param("verbose")
             .build())
    assert result == ["test-cmd", "backup", "--source", "/path", "--verbose"]

def test_reset(builder):
    """Test resetting the builder"""
    builder.param("verbose")
    builder.clear()
    result = builder.build()
    assert result == ["test-cmd"]

def test_different_parameter_styles():
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

def test_list_positional_parameters():
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

def test_list_separate_parameters(builder):
    """Test parameters with list values using separate style"""
    result = (builder
             .param("tags", ["tag1", "tag2", "tag3"])
             .build())
    assert result == ["test-cmd", "--tags", "tag1", "--tags", "tag2", "--tags", "tag3"]

def test_list_joined_parameters():
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

def test_synopsis_parameters():
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
    assert result == ["test-cmd", "abc123", "/path/to/dir"]  # Optional parameter should be included when provided
    
    # Test with flags and synopsis parameters
    result = builder.param("verbose").build(synopsis_values={"snapshotID": "abc123"})
    assert result == ["test-cmd", "--verbose", "abc123"]
    
    # Test missing required synopsis parameter
    with pytest.raises(ValueError):
        builder.build(synopsis_values={})

def test_synopsis_parameters_with_subcommands():
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

# Tests for ParameterStyle
def test_equality_with_same_style():
    """Test equality between two ParameterStyle instances with same value."""
    style1 = ParameterStyle.SEPARATE
    style2 = ParameterStyle.SEPARATE
    assert style1 == style2
    assert not (style1 != style2)

def test_equality_with_string():
    """Test equality between ParameterStyle and string."""
    style = ParameterStyle.JOINED
    assert style == "joined"
    assert style == "JOINED"  # Case insensitive
    assert not (style != "joined")
    assert not (style != "JOINED")

def test_inequality_with_different_style():
    """Test inequality between different ParameterStyle values."""
    style1 = ParameterStyle.SEPARATE
    style2 = ParameterStyle.JOINED
    assert style1 != style2
    assert style1 != style2

def test_inequality_with_none():
    """Test inequality with None value."""
    style = ParameterStyle.SEPARATE
    assert style != None
    assert style != None

def test_inequality_with_other_types():
    """Test inequality with other types."""
    style = ParameterStyle.SEPARATE
    assert style != 42
    assert style != True
    assert style != 42
    assert style != True