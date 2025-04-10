"""Command builder utilities for constructing command line arguments."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

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

    def format_param_name(self, use_short_form: bool = False) -> str:
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

        if style == ParameterStyle.POSITIONAL:
            return name
        if style == ParameterStyle.SINGLE_DASH:
            return f"-{name}"
        if style == ParameterStyle.DOUBLE_DASH:
            return f"--{name}"
        if style == ParameterStyle.SEPARATE:
            return f"--{name}" if not use_short_form else f"-{name}"
        return f"--{name}"  # Default to double dash
    
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
                 default_param_style: Union[str, ParameterStyle] = ParameterStyle.SEPARATE):
        """Initialize the command definition.
        
        Args:
            name: Name/executable of the command.
            parameters: Dictionary mapping parameter names to their definitions.
            subcommands: Dictionary mapping subcommand names to their definitions.
            default_param_style: Default style for parameters that don't specify one.
        """
        self.name = name
        # Always initialize parameters as empty dict if None
        self.parameters = parameters if parameters is not None else {}
        # Always initialize subcommands as empty dict if None  
        self.subcommands = subcommands if subcommands is not None else {}
        
        self.default_param_style = default_param_style


class CommandBuilder:
    """A flexible command builder for constructing command line arguments.
    
    This class can be used to build command line arguments for any executable
    based on a provided command definition that specifies the structure and
    rules for the command.
    
    Example:
        # Define a command structure
        git_command = CommandDefinition(
            name="git",
            parameters=[
                CommandParameter("verbose", prefix="-", required=False),
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
               .with_parameter("verbose")
               .with_parameter("config", "user.name=John")
               .with_subcommand("commit")
               .with_parameter("message", "Initial commit")
               .build())
        
        # Result: ['git', '-v', '--config', 'user.name=John', 'commit', '-m', 'Initial commit']
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
    
    def with_parameter(self, name: str, value: Any = None, use_short_form: bool = False, **kwargs) -> 'CommandBuilder':
        """Add a parameter to the command.
        
        Args:
            name: Name of the parameter to add. The parameter will be created with default
                style if it doesn't exist.
            value: Value for the parameter, if any. Can be a single value or a list of values.
            use_short_form: If True, use short form of parameter if available.
            
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
        self._use_short_forms[name] = use_short_form
        return self
    
    def with_subcommand(self, name: str) -> 'CommandBuilder':
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
    
    def build(self, use_short_form: bool = False) -> List[str]:
        """Build the final command line arguments list.
        
        Args:
            use_short_form: If True, use short form for all parameters where available,
                unless overridden by individual parameter settings.

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
            use_short = self._use_short_forms.get(param.name, use_short_form)
            param_str = param.format_param_name(use_short_form=use_short)
            
            # Handle different value types
            if isinstance(value, list):
                # List values are always handled as separate name/value pairs
                for item in value:
                    if param.style == ParameterStyle.JOINED:
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
                    if param.style == ParameterStyle.JOINED:
                        # Joined parameters combine name and value with =
                        result.append(f"{param_str}={value}")
                    else:
                        # All other styles separate name and value
                        result.extend([param_str, str(value)])
        
        return result
    
    def reset(self) -> 'CommandBuilder':
        """Reset the builder to its initial state.
        
        Returns:
            Self for method chaining.
        """
        self._current_def = self._command_def
        self._parameters = {}
        self._command_chain = [self._command_def.name]
        return self
