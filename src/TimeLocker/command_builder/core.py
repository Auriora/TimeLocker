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

import subprocess
from enum import Enum
from typing import Dict, List, Optional, Union


class ParameterStyle(Enum):
    SEPARATE = "separate"  # --param value
    JOINED = "joined"  # --param=value
    DOUBLE_DASH = "double_dash"  # --param
    SINGLE_DASH = "single_dash"  # -param
    POSITIONAL = "positional"  # value

    def __eq__(self, other):
        if isinstance(other, ParameterStyle):
            return self.value == other.value
        elif isinstance(other, str):
            return self.value.upper() == other.upper()
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


class CommandParameter:
    def __init__(
            self,
            name: str,
            style: ParameterStyle = ParameterStyle.SEPARATE,
            required: bool = False,
            value_required: bool = True,
            prefix: str = "--",
            position: Optional[int] = None,
            short_name: Optional[str] = None,
            short_style: Optional[ParameterStyle] = None,
            description: str = "",
    ):
        self.name = name
        self.style = style
        self.required = required
        self.value_required = value_required
        self.prefix = prefix
        self.position = position
        self.short_name = short_name
        self.short_style = short_style
        self.description = description


class CommandDefinition:
    def __init__(
            self,
            name: str,
            parameters: Dict[str, CommandParameter] = None,
            subcommands: Dict[str, "CommandDefinition"] = None,
            default_param_style: ParameterStyle = ParameterStyle.SEPARATE,
            synopsis_params: List[str] = None,
    ):
        self.name = name
        self.parameters = parameters or {}
        self.subcommands = subcommands or {}
        self.default_param_style = default_param_style
        self.synopsis_params = synopsis_params or []


class CommandBuilder:
    def __init__(self, definition: CommandDefinition):
        self.definition = definition
        self.current_command = definition
        self.params: Dict[str, Optional[Union[str, List[str]]]] = {}
        self.command_chain: List[str] = []

    def param(self, name: str, value: Union[str, List[str]] = None) -> "CommandBuilder":
        # Look for parameter in current command first, then in global command
        param_def = None
        if name in self.current_command.parameters:
            param_def = self.current_command.parameters[name]
        elif name in self.definition.parameters:
            param_def = self.definition.parameters[name]
        else:
            raise ValueError(f"Unknown parameter: {name}")
        if (
                param_def.value_required
                and value is None
                and param_def.style
                not in [ParameterStyle.DOUBLE_DASH, ParameterStyle.SINGLE_DASH]
        ):
            raise ValueError(f"Parameter {name} requires a value")

        # Handle multiple values for the same parameter
        if name in self.params:
            # Convert existing value to list if it isn't already
            existing_value = self.params[name]
            if not isinstance(existing_value, list):
                existing_value = [existing_value] if existing_value is not None else []

            # Add new value to the list
            if isinstance(value, list):
                existing_value.extend(value)
            else:
                existing_value.append(value)

            self.params[name] = existing_value
        else:
            self.params[name] = value
        return self

    def command(self, name: str) -> "CommandBuilder":
        if name not in self.definition.subcommands:
            raise ValueError(f"Unknown subcommand: {name}")

        self.command_chain.append(name)
        self.current_command = self.definition.subcommands[name]
        return self

    def clear(self) -> "CommandBuilder":
        self.params.clear()
        self.command_chain.clear()
        self.current_command = self.definition
        return self

    def build(
            self, synopsis_values: Dict[str, str] = None, use_short_form: bool = False
    ) -> List[str]:
        result = [self.definition.name]

        # Add subcommands
        result.extend(self.command_chain)

        # Add parameters
        for name, value in self.params.items():
            # Look for parameter in current command first, then in global command
            param_def = None
            if name in self.current_command.parameters:
                param_def = self.current_command.parameters[name]
            elif name in self.definition.parameters:
                param_def = self.definition.parameters[name]
            else:
                raise ValueError(f"Unknown parameter: {name}")

            # Handle callable values (like methods)
            if callable(value):
                value = value()

            # Determine parameter name and style based on use_short_form
            param_name = (
                    param_def.short_name
                    if use_short_form and param_def.short_name
                    else name
            )
            param_style = (
                    param_def.short_style
                    if use_short_form and param_def.short_style
                    else param_def.style
            )
            param_prefix = (
                    "-" if param_style == ParameterStyle.SINGLE_DASH else param_def.prefix
            )

            # Handle list values
            if isinstance(value, list):
                for v in value:
                    if param_style == ParameterStyle.DOUBLE_DASH:
                        result.append(f"{param_prefix}{param_name}")
                        if v is not None:
                            result.append(v)
                    elif param_style == ParameterStyle.SINGLE_DASH:
                        result.append(f"-{param_name}")
                        if v is not None:
                            result.append(v)
                    elif param_style == ParameterStyle.SEPARATE:
                        result.append(f"{param_prefix}{param_name}")
                        if v is not None:
                            result.append(v)
                    elif param_style == ParameterStyle.JOINED:
                        if v is not None:
                            result.append(f"{param_prefix}{param_name}={v}")
                        else:
                            result.append(f"{param_prefix}{param_name}")
                    elif param_style == ParameterStyle.POSITIONAL:
                        result.append(param_name)
                        if v is not None:
                            result.append(v)
                continue

            # Handle single values
            if param_style == ParameterStyle.DOUBLE_DASH:
                result.append(f"{param_prefix}{param_name}")
                if value is not None:
                    result.append(value)
            elif param_style == ParameterStyle.SINGLE_DASH:
                result.append(f"-{param_name}")
                if value is not None:
                    result.append(value)
            elif param_style == ParameterStyle.SEPARATE:
                # For short form parameters, always use single dash
                prefix = (
                        "-" if use_short_form and param_def.short_name else param_prefix
                )
                result.append(f"{prefix}{param_name}")
                if value is not None:
                    result.append(value)
            elif param_style == ParameterStyle.JOINED:
                if value is not None:
                    result.append(f"{param_prefix}{param_name}={value}")
                else:
                    result.append(f"{param_prefix}{param_name}")
            elif param_style == ParameterStyle.POSITIONAL:
                if value is not None:
                    result.append(value)

        # Add synopsis parameters
        synopsis_values = synopsis_values or {}
        for param in self.current_command.synopsis_params:
            is_optional = param.startswith("[") and param.endswith("...]")
            param_name = param.strip("[].")
            if param_name in synopsis_values:
                result.append(synopsis_values[param_name])
            elif not is_optional:
                raise ValueError(f"Required synopsis parameter {param_name} is missing")

        return result

    def run(self, env: Optional[Dict[str, str]] = None,
            synopsis_values: Dict[str, str] = None,
            use_short_form: bool = False) -> str:
        """
        Execute the command and return the output

        Args:
            env: Environment variables to set for the command
            synopsis_values: Values for synopsis parameters
            use_short_form: Whether to use short form parameters

        Returns:
            str: Command output

        Raises:
            subprocess.CalledProcessError: If command fails
            FileNotFoundError: If command executable not found
        """
        command_list = self.build(synopsis_values, use_short_form)

        # Merge environment variables
        process_env = {}
        if env:
            process_env.update(env)

        # Execute command
        result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                env=process_env if process_env else None,
                check=True
        )

        return result.stdout
