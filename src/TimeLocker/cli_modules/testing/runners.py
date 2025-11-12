"""
CLI test runners and execution helpers.

Provides utilities for running CLI commands in tests with
consistent configuration and output handling.
"""

from typing import Any, Dict, List, Optional, Tuple
from typer.testing import CliRunner
from pathlib import Path
import os


class CLITestRunner:
    """
    Enhanced CLI test runner with additional features.
    
    This class wraps the Typer CliRunner with additional functionality
    for consistent test execution and output handling.
    """
    
    def __init__(
        self,
        columns: int = 200,
        env: Optional[Dict[str, str]] = None,
        mix_stderr: bool = True
    ):
        """
        Initialize the CLI test runner.
        
        Args:
            columns: Terminal width for output formatting
            env: Environment variables for test execution
            mix_stderr: Whether to mix stderr with stdout (not used, for compatibility)
        """
        self.columns = columns
        self.env = env or {}
        self.mix_stderr = mix_stderr
        
        # Set default environment for tests
        self.env.setdefault('COLUMNS', str(columns))
        self.env.setdefault('TIMELOCKER_TEST_MODE', '1')
        
        self._runner = CliRunner(env=self.env)
    
    def invoke(
        self,
        app,
        args: List[str],
        input: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        catch_exceptions: bool = True,
        **kwargs
    ):
        """
        Invoke a CLI command.
        
        Args:
            app: Typer app to invoke
            args: Command arguments
            input: Input to provide to command
            env: Additional environment variables
            catch_exceptions: Whether to catch exceptions
            **kwargs: Additional arguments for CliRunner.invoke
        
        Returns:
            CliRunner result object
        """
        # Merge environment variables
        merged_env = {**self.env}
        if env:
            merged_env.update(env)
        
        return self._runner.invoke(
            app,
            args,
            input=input,
            env=merged_env,
            catch_exceptions=catch_exceptions,
            **kwargs
        )
    
    def invoke_with_config(
        self,
        app,
        args: List[str],
        config_dir: Optional[Path] = None,
        **kwargs
    ):
        """
        Invoke a CLI command with specific config directory.
        
        Args:
            app: Typer app to invoke
            args: Command arguments
            config_dir: Configuration directory path
            **kwargs: Additional arguments for invoke
        
        Returns:
            CliRunner result object
        """
        env = kwargs.pop('env', {})
        if config_dir:
            env['TIMELOCKER_CONFIG_DIR'] = str(config_dir)
        
        return self.invoke(app, args, env=env, **kwargs)
    
    def invoke_interactive(
        self,
        app,
        args: List[str],
        inputs: List[str],
        **kwargs
    ):
        """
        Invoke a CLI command with interactive inputs.
        
        Args:
            app: Typer app to invoke
            args: Command arguments
            inputs: List of inputs to provide (one per prompt)
            **kwargs: Additional arguments for invoke
        
        Returns:
            CliRunner result object
        """
        input_str = '\n'.join(inputs) + '\n'
        return self.invoke(app, args, input=input_str, **kwargs)
    
    def get_output(self, result) -> str:
        """
        Get combined output from result.
        
        Args:
            result: CliRunner result object
        
        Returns:
            Combined stdout and stderr
        """
        stdout = result.stdout or ""
        stderr = getattr(result, "stderr", "") or ""
        return stdout + "\n" + stderr


def get_test_runner(
    columns: int = 200,
    env: Optional[Dict[str, str]] = None
) -> CLITestRunner:
    """
    Get a configured CLI test runner.
    
    Args:
        columns: Terminal width for output formatting
        env: Environment variables for test execution
    
    Returns:
        Configured CLITestRunner instance
    """
    return CLITestRunner(columns=columns, env=env)


def run_cli_command(
    app,
    args: List[str],
    input: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    **kwargs
) -> Tuple[int, str]:
    """
    Run a CLI command and return exit code and output.
    
    This is a convenience function for simple command execution
    without needing to create a runner instance.
    
    Args:
        app: Typer app to invoke
        args: Command arguments
        input: Input to provide to command
        env: Environment variables
        **kwargs: Additional arguments for CliRunner.invoke
    
    Returns:
        Tuple of (exit_code, combined_output)
    """
    runner = get_test_runner(env=env)
    result = runner.invoke(app, args, input=input, **kwargs)
    output = runner.get_output(result)
    return result.exit_code, output


def create_test_environment(
    tmp_path: Path,
    create_config: bool = True,
    create_cache: bool = True,
    create_data: bool = True
) -> Dict[str, Path]:
    """
    Create a test environment with isolated directories.
    
    Args:
        tmp_path: Temporary path for test environment
        create_config: Whether to create config directory
        create_cache: Whether to create cache directory
        create_data: Whether to create data directory
    
    Returns:
        Dictionary mapping directory types to paths
    """
    env_dirs = {}
    
    if create_config:
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        env_dirs['config'] = config_dir
    
    if create_cache:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        env_dirs['cache'] = cache_dir
    
    if create_data:
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        env_dirs['data'] = data_dir
    
    return env_dirs


def get_test_environment_vars(env_dirs: Dict[str, Path]) -> Dict[str, str]:
    """
    Get environment variables for test environment.
    
    Args:
        env_dirs: Dictionary of environment directories
    
    Returns:
        Dictionary of environment variables
    """
    env_vars = {
        'TIMELOCKER_TEST_MODE': '1',
    }
    
    if 'config' in env_dirs:
        env_vars['TIMELOCKER_CONFIG_DIR'] = str(env_dirs['config'])
        env_vars['XDG_CONFIG_HOME'] = str(env_dirs['config'])
    
    if 'cache' in env_dirs:
        env_vars['XDG_CACHE_HOME'] = str(env_dirs['cache'])
    
    if 'data' in env_dirs:
        env_vars['XDG_DATA_HOME'] = str(env_dirs['data'])
    
    return env_vars


def setup_test_cli_environment(tmp_path: Path) -> Tuple[CLITestRunner, Dict[str, Path]]:
    """
    Set up a complete test CLI environment.
    
    This is a convenience function that creates all necessary directories
    and returns a configured runner.
    
    Args:
        tmp_path: Temporary path for test environment
    
    Returns:
        Tuple of (runner, environment_directories)
    """
    env_dirs = create_test_environment(tmp_path)
    env_vars = get_test_environment_vars(env_dirs)
    runner = get_test_runner(env=env_vars)
    
    return runner, env_dirs
