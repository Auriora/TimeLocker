# Command Builder Usage Guide

The `CommandBuilder` class provides a flexible way to construct command line arguments for any executable based on a configuration-driven approach. This guide explains how to use the command builder effectively.

## Basic Concepts

The command builder is based on three main concepts:

1. `CommandParameter` - Defines a single parameter or flag that can be passed to a command
2. `CommandDefinition` - Defines the structure of a command, including its parameters and sub-commands
3. `CommandBuilder` - The builder itself that constructs command lines based on the definition

## Parameter Styles

Parameters can be formatted in three different styles:

- `SEPARATE`: Parameters and values are separate arguments (e.g. `--param value`)
- `JOINED`: Parameters and values are joined with = (e.g. `--param=value`)
- `POSITIONAL`: Only the value is included (e.g. `value`)

## Example Usage

Here's an example of how to define and use a command builder for a git-like command:

```python
from utils.command_builder import CommandBuilder, CommandDefinition, CommandParameter, ParameterStyle

# Define the command structure
git_command = CommandDefinition(
    name="git",
    parameters=[
        CommandParameter("verbose", prefix="-", required=False, value_required=False),
        CommandParameter("config", required=False),
    ],
    subcommands={
        "commit": CommandDefinition(
            name="commit",
            parameters=[
                CommandParameter("message", prefix="-", required=True),
                CommandParameter("amend", prefix="--", value_required=False),
            ]
        )
    }
)

# Create a builder
builder = CommandBuilder(git_command)

# Build a command
cmd = (builder
       .param("verbose")
       .param("config", "user.name=John")
       .command("commit")
       .param("message", "Initial commit")
       .build())

# Result: ['git', '-v', '--config', 'user.name=John', 'commit', '-m', 'Initial commit']
```

## Restic Example

Here's how you might define the command structure for Restic:

```python
restic_command = CommandDefinition(
    name="restic",
    parameters=[
        CommandParameter("repo", prefix="-", required=True),
    ],
    subcommands={
        "backup": CommandDefinition(
            name="backup",
            parameters=[
                CommandParameter("exclude", required=False),
                CommandParameter("iexclude", required=False),
                CommandParameter("tag", required=False),
                # Add other backup parameters
            ]
        ),
        "restore": CommandDefinition(
            name="restore",
            parameters=[
                CommandParameter("target", required=True),
                CommandParameter("snapshot-id", required=True),
                # Add other restore parameters
            ]
        )
        # Add other subcommands
    }
)
```

## Best Practices

1. **Define Required Parameters**: Mark parameters as required when they must be provided:
```python
CommandParameter("repo", required=True)
```

2. **Use Parameter Styles**: Choose the appropriate style for each parameter:
```python
CommandParameter("output", style=ParameterStyle.JOINED)  # --output=json
```

3. **Position Parameters**: Use position for ordered arguments:
```python
CommandParameter("source", position=0, style=ParameterStyle.POSITIONAL)
```

4. **Reset Between Commands**: Call reset() when reusing a builder:

```python
builder.clear().param("verbose").build()
```

## Error Handling

The command builder will raise `ValueError` in these cases:
- When a required parameter is missing
- When trying to use an undefined parameter
- When trying to use an undefined subcommand
- When a parameter requires a value but none is provided

## Type Hints

The command builder supports type hints and chain-able methods:

```python
builder: CommandBuilder
result: List[str] = builder.param("verbose").build()
```

---

> Copyright ©  Bruce Cherrington
>
> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
> 
> This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
> 
> You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
