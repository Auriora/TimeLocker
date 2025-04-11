"""Command builder utilities for constructing command line arguments."""
import os
from subprocess import run, Popen, PIPE, STDOUT, SubprocessError, CalledProcessError

from typing import Callable, Dict, List
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class CommandExecutionError(Exception):
    def __init__(self, message, stderr=None):
        super().__init__(message)
        self.stderr = stderr

class ParameterStyle(Enum):
    """Defines how parameters should be formatted in the command."""
    
    SEPARATE = "separate"  # Parameters are separate: --param value
    JOINED = "joined"  # Parameters are joined: --param=value
    POSITIONAL = "positional"  # Parameters are positional: value
    SINGLE_DASH = "single_dash"  # Parameters use single dash: -param value
    DOUBLE_DASH = "double_dash"  # Parameters use double dash: --param value

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        if isinstance(other, ParameterStyle):
            return self.value.lower() == other.value.lower()  # Compare by value
        return False
    
    def __str__(self):
        return self.value
    
    def __hash__(self):
        return hash(self.value.lower())


@dataclass
class CommandParameter:
    """Represents a command parameter configuration."""

    def format_param_name(self, use_short_form: bool = False) -> (str, str):
        """Format the parameter name according to its style.
        
        Args:
            use_short_form: If True, use short form of parameter if available.
        
        Returns:
            Formatted parameter string based on style.
        """
        if use_short_form and hasattr(self, 'short_name') and self.short_name:
            name = self.short_name
            style = self.short_style if hasattr(self, 'short_style') and self.short_style else ParameterStyle.SINGLE_DASH
        else:
            name = self.name
            style = self.style

        parameter = f"--{name}"
        if style == ParameterStyle.POSITIONAL:
            parameter = name
        elif style == ParameterStyle.SINGLE_DASH:
            parameter = f"-{name}"
        elif style == ParameterStyle.DOUBLE_DASH:
            parameter = f"--{name}"
        elif style == ParameterStyle.SEPARATE:
            parameter = f"--{name}" if not use_short_form else f"-{name}"
        return parameter, style
    
    @staticmethod
    def _convert_style(style: Union[str, 'ParameterStyle', None]) -> 'ParameterStyle':
        """Convert input to ParameterStyle enum value.
        
        Args:
            style: Input style as string or enum.
            
        Returns:
            ParameterStyle enum value.
        """
        print(f"Converting style: {style!r}, type={type(style)}")  # Debug
        if style is None:
            result = ParameterStyle.SEPARATE
        elif isinstance(style, ParameterStyle):
            result = style
        elif isinstance(style, str):
            try:
                result = next((ps for ps in ParameterStyle if ps == style), ParameterStyle.SEPARATE)
            except (KeyError, ValueError):
                result = ParameterStyle.SEPARATE
        else:
            result = ParameterStyle.SEPARATE
        print(f"Converted to: {result!r}")  # Debug
        return result
    
    name: str
    style: Union[str, ParameterStyle] = ParameterStyle.SEPARATE
    short_name: Optional[str] = None
    short_style: Optional[Union[str, ParameterStyle]] = None
    prefix: Optional[str] = None
    required: bool = False
    position: Optional[int] = None
    value_required: bool = False
    description: str = ""
    
    def __post_init__(self):
        """Initialize parameter settings after creation."""
        print(f"[post_init] Before convert - Parameter {self.name}: style={self.style!r}")  # Debug
        self.style = self._convert_style(self.style)
        print(f"[post_init] After convert - Parameter {self.name}: style={self.style!r}")  # Debug
            
        # Always reset and calculate prefix based on current style
        if self.style == ParameterStyle.POSITIONAL:
            self.prefix = ""  # Positional parameters never have prefix
        elif self.style == ParameterStyle.SINGLE_DASH:
            self.prefix = "-"
        elif self.style == ParameterStyle.DOUBLE_DASH:
            self.prefix = "--" 
        else:
            self.prefix = "--"  # Default to double dash for other styles
            
        # Set value_required based on parameter style - only joined and positional require values
        required_styles = {ParameterStyle.JOINED, ParameterStyle.POSITIONAL}
        self.value_required = any(self.style.value.lower() == style.value.lower() for style in required_styles)


class CommandDefinition:
    """Defines the structure and rules for a command."""
    
    def __init__(self, name: str, parameters: Optional[Dict[str, Any]] = None,
                 subcommands: Optional[Dict[str, 'CommandDefinition']] = None,
                 default_param_style: Union[str, ParameterStyle] = ParameterStyle.SEPARATE,
                 synopsis_params: Optional[List[str]] = None):
        """Initialize the command definition.
        
        Args:
            name: Name/executable of the command.
            parameters: Dictionary mapping parameter names to their definitions.
            subcommands: Dictionary mapping subcommand names to their definitions.
            default_param_style: Default style for parameters that don't specify one.
            synopsis_params: List of synopsis parameters from the command definition.
        """
        self.name = name
        # Always initialize parameters as empty dict if None
        self.parameters = parameters if parameters is not None else {}
        # Always initialize subcommands as empty dict if None  
        self.subcommands = subcommands if subcommands is not None else {}
        # Store synopsis parameters
        self.synopsis_params = synopsis_params if synopsis_params is not None else []
        
        self.default_param_style = default_param_style


class CommandBuilder:
    """
    Builds and manages a command structure according to a predefined definition.

    This class is used to construct command-line style arguments based on a predefined
    command definition structure. It supports chaining methods to dynamically build and
    configure commands, parameters, and subcommands. The definition enables validation
    and ensures proper structure for commands and output.

    :ivar _command_def: The primary `CommandDefinition` instance used for command structure.
    :type _command_def: CommandDefinition
    :ivar _current_def: The current `CommandDefinition` context being processed.
    :type _current_def: CommandDefinition
    :ivar _parameters: Dictionary containing user-provided parameter values.
    :type _parameters: Dict[str, Any]
    :ivar _command_chain: List representing the sequence of subcommands in the command.
    :type _command_chain: List[str]
    """

    def __init__(self, command_def: CommandDefinition):
        """Initialize the command builder.
        
        Args:
            command_def: Definition of the command structure and rules.
        """
        # Convert command definition's parameters and styles
        if isinstance(command_def.default_param_style, str):
            try:
                command_def.default_param_style = ParameterStyle(command_def.default_param_style.lower())
            except ValueError:
                command_def.default_param_style = ParameterStyle.SEPARATE

        # Initialize parameter dictionary if needed
        if command_def.parameters is None:
            command_def.parameters = {}
        
        # Ensure all parameters are CommandParameter instances
        for name, param in list(command_def.parameters.items()):
            if not isinstance(param, CommandParameter):
                if isinstance(param, str):
                    command_def.parameters[name] = CommandParameter(name=name, style=command_def.default_param_style)
                elif isinstance(param, dict):
                    command_def.parameters[name] = CommandParameter(
                        name=name, style=command_def.default_param_style, **param
                    )

        # Initialize subcommands
        if command_def.subcommands is None:
            command_def.subcommands = {}
            
        self._command_def = command_def
        self._current_def = command_def
        self._parameters: Dict[str, Any] = {}
        self._command_chain: List[str] = [command_def.name]
    
    def param(self, name: str, value: Any = None, **kwargs) -> 'CommandBuilder':
        """Add a parameter to the command.
        
        Args:
            name: Name of the parameter to add. The parameter will be created with default
                style if it doesn't exist.
            value: Value for the parameter, if any. Can be a single value or a list of values.

        Returns:
            Self for method chaining.
            
        Raises:
            ValueError: If required value is missing.
        """
        # Validate parameter exists in command definition
        if name not in self._current_def.parameters:
            raise ValueError(f"Parameter '{name}' is not defined in command definition")
            
        param = self._current_def.parameters[name]
        
        # Style updates through kwargs are no longer allowed - parameters must be pre-defined
        if 'style' in kwargs:
            raise ValueError("Parameter style cannot be modified after definition")
            
        # Check if value is required but missing
        if value is None and param.value_required:
            raise ValueError(f"Parameter '{name}' requires a value")

        self._parameters[name] = value
        return self
    
    def command(self, name: str) -> 'CommandBuilder':
        """Add a subcommand to the command chain.
        
        Args:
            name: Name of the subcommand to add.
            
        Returns:
            Self for method chaining.
            
        Raises:
            ValueError: If subcommand doesn't exist.
        """
        if name not in self._current_def.subcommands:
            raise ValueError(f"Unknown subcommand: {name}")
            
        self._current_def = self._current_def.subcommands[name]
        self._command_chain.append(name)
        return self
    
    def build(self, use_short_form: bool = False, synopsis_values: Optional[Dict[str, str]] = None) -> List[str]:
        """Build the final command line arguments list.
        
        Args:
            use_short_form: If True, use short form for all parameters where available,
                unless overridden by individual parameter settings.
            synopsis_values: Dictionary mapping synopsis parameter names to their values.
                For example: {"snapshot ID": "abc123", "dir": "/path/to/dir"}

        Returns:
            List of command line arguments.
            
        Raises:
            ValueError: If required parameters are missing.
        """
        result = self._command_chain.copy()
        
        # Debug: Print parameter state
        for name, param in self._current_def.parameters.items():
            print(f"Parameter '{name}': style={param.style!r}, value={param.style.value!r}, prefix='{param.prefix}'")
            print(f"Style comparison: {param.style == ParameterStyle.POSITIONAL}, type={type(param.style)}")
        
        # Convert parameters to list and sort by position
        params = list(self._current_def.parameters.values())
        params.sort(key=lambda p: p.position if p.position is not None else float('inf'))
        
        # Check required parameters
        missing = [
            p.name for p in params
            if p.required and p.name not in self._parameters
        ]
        if missing:
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")
        
        # Add parameters in correct order
        for param in params:
            if param.name not in self._parameters:
                continue
                
            value = self._parameters[param.name]
            
            # Get formatted parameter name with appropriate form
            param_str, param_style   = param.format_param_name(use_short_form=use_short_form)
            
            # Handle different value types
            if isinstance(value, list):
                # List values are always handled as separate name/value pairs
                for item in value:
                    if param_style == ParameterStyle.JOINED:
                        # Joined parameters combine name and value with =
                        result.append(f"{param_str}={str(item)}")
                    else:
                        # All other styles separate name and value
                        result.extend([param_str, str(item)])
            else:
                if value is None and not param.value_required:
                    # Flag parameter without value
                    result.append(param_str)
                elif value is not None:
                    if param_style == ParameterStyle.JOINED:
                        # Joined parameters combine name and value with =
                        result.append(f"{param_str}={value}")
                    else:
                        # All other styles separate name and value
                        result.extend([param_str, str(value)])
        
        # Add synopsis parameters in order and validate required ones
        synopsis_values = synopsis_values or {}
        for param in self._current_def.synopsis_params:
            # Remove optional brackets and ... from parameter name
            param_name = param.strip('[]').rstrip('...')
            if param_name in synopsis_values:
                # Add the value if provided, regardless of whether parameter is optional
                result.append(synopsis_values[param_name])
            elif not param.startswith('['):  # Required parameter
                raise ValueError(f"Missing required synopsis parameter: {param_name}")
        
        return result
    
    def clear(self) -> 'CommandBuilder':
        """Reset the builder to its initial state by clearing all commands and parameters
        
        Returns:
            Self for method chaining.
        """
        self._current_def = self._command_def
        self._parameters = {}
        self._command_chain = [self._command_def.name]
        return self

    @staticmethod
    def _merge_envs(env1: Dict[str, str], env2: Dict[str, str]) -> Dict[str, str]:
        if env1 is None:
            env1 = {}
        merged_env = {**env1, **env2}
        return merged_env

    def run(self, callback: Callable[[str], None] = None, env: Dict[str, str] = None, synopsis_values: Optional[Dict[str, str]] = None) -> str:
        command = self.build(synopsis_values=synopsis_values)
        try:
            process = Popen(
                command,
                env=self._merge_envs(env, dict(os.environ)),
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
                bufsize=1
            )
        except SubprocessError as e:
            raise CommandExecutionError(f"Failed to start command: {' '.join(command)}", stderr=str(e))

        output = []
        for line in process.stdout:
            output.append(line)
            if callback:
                callback(line.strip())

        process.communicate()
        return_code = process.returncode
        if return_code != 0:
            raise CommandExecutionError(
                f"Command failed with return code {return_code}: {' '.join(command)}", stderr=''.join(output))

        return ''.join(output)

    def run_iter(self, env: Dict[str, str], synopsis_values: Optional[Dict[str, str]] = None):
        command = self.build(synopsis_values=synopsis_values)
        try:
            process = Popen(
                command,
                env=self._merge_envs(env, dict(os.environ)),
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
                bufsize=1
            )
        except SubprocessError as e:
            raise CommandExecutionError(f"Failed to start command: {' '.join(command)}", stderr=str(e))

        while True:
            try:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    yield line.strip()
            except IOError as e:
                raise CommandExecutionError(f"Error reading command output: {' '.join(command)}", stderr=str(e))

        if process.returncode != 0:
            raise CommandExecutionError(f"Command failed: {' '.join(command)}", stderr="Process failed with non-zero exit code")





