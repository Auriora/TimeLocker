#!/usr/bin/env python3
"""
CLI Command Extraction Script

Automates the extraction of command groups from the monolithic cli.py
into modular command files following Phase 3 patterns.

Usage:
    python scripts/extract_cli_commands.py --module security
    python scripts/extract_cli_commands.py --module all
    python scripts/extract_cli_commands.py --list
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import argparse


@dataclass
class CommandInfo:
    """Information about a command."""
    name: str
    function_name: str
    start_line: int
    end_line: int
    decorator_line: int


@dataclass
class ModuleInfo:
    """Information about a command module."""
    name: str
    app_name: str
    description: str
    commands: List[CommandInfo]
    estimated_lines: int
    priority: int


# Module definitions
MODULES = {
    "security": ModuleInfo(
        name="security",
        app_name="security_app",
        description="Security management commands",
        commands=[],
        estimated_lines=300,
        priority=1
    ),
    "credentials": ModuleInfo(
        name="credentials",
        app_name="credentials_app",
        description="Credential management commands",
        commands=[],
        estimated_lines=400,
        priority=2
    ),
    "snapshots": ModuleInfo(
        name="snapshots",
        app_name="snapshots_app",
        description="Snapshot operations",
        commands=[],
        estimated_lines=800,
        priority=3
    ),
    "repositories": ModuleInfo(
        name="repos",
        app_name="repos_app",
        description="Repository operations",
        commands=[],
        estimated_lines=1200,
        priority=4
    ),
    "config": ModuleInfo(
        name="config",
        app_name="config_app",
        description="Configuration management commands",
        commands=[],
        estimated_lines=1500,
        priority=5
    ),
}


def find_commands_in_cli(cli_file: Path, app_name: str) -> List[CommandInfo]:
    """
    Find all commands for a specific app in cli.py.
    
    Args:
        cli_file: Path to cli.py
        app_name: Name of the Typer app (e.g., 'security_app')
        
    Returns:
        List of CommandInfo objects
    """
    with open(cli_file, 'r') as f:
        lines = f.readlines()
    
    commands = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Look for @app_name.command("name")
        match = re.match(rf'@{app_name}\.command\(["\'](\w+)["\']\)', line.strip())
        if match:
            command_name = match.group(1)
            decorator_line = i
            
            # Find the function definition (next non-empty line)
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('def '):
                j += 1
            
            if j < len(lines):
                func_match = re.match(r'def (\w+)\(', lines[j].strip())
                if func_match:
                    function_name = func_match.group(1)
                    start_line = i
                    
                    # Find the end of the function (next function or decorator)
                    k = j + 1
                    indent_level = len(lines[j]) - len(lines[j].lstrip())
                    
                    while k < len(lines):
                        current_line = lines[k]
                        if current_line.strip():
                            current_indent = len(current_line) - len(current_line.lstrip())
                            # End when we hit a line at same or lower indent that starts a new definition
                            if current_indent <= indent_level and (
                                current_line.strip().startswith('def ') or
                                current_line.strip().startswith('@') or
                                current_line.strip().startswith('class ')
                            ):
                                break
                        k += 1
                    
                    end_line = k
                    
                    commands.append(CommandInfo(
                        name=command_name,
                        function_name=function_name,
                        start_line=start_line,
                        end_line=end_line,
                        decorator_line=decorator_line
                    ))
                    
                    i = k
                    continue
        
        i += 1
    
    return commands


def get_module_specific_imports(module_name: str) -> str:
    """Get module-specific imports based on module name."""
    imports = {
        "security": '''# Security-specific imports
from TimeLocker.security import (
    SecurityService,
    CredentialManager,
    AccessManager,
    RepositoryInfo,
    RepositoryMode,
    ConfirmationDialogs
)
from TimeLocker.completion import repository_completer
from datetime import datetime, timedelta''',
        
        "credentials": '''# Credential management
from TimeLocker.security.credential_manager import (
    CredentialManager,
    CredentialManagerError
)
from TimeLocker.config.configuration_manager import ConfigurationManager
from TimeLocker.completion import repository_name_completer
from getpass import getpass''',
        
        "snapshots": '''# Snapshot management
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.restore_manager import RestoreManager
from TimeLocker.backup_manager import BackupManager
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.interfaces.exceptions import ConfigurationError
from TimeLocker.completion import (
    snapshot_id_completer,
    repository_completer,
    file_path_completer
)
from TimeLocker.utils.repository_resolver import (
    validate_repository_name_or_uri,
    resolve_repository_uri,
    get_default_repository
)
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format
from datetime import datetime
import subprocess''',
        
        "repositories": '''# Repository management
from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.services.repository_service import RepositoryService
from TimeLocker.services.repository_factory import RepositoryFactory
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.config import ConfigurationModule
from TimeLocker.security import (
    SecurityService,
    CredentialManager,
    RepositoryInfo,
    RepositoryMode
)
from TimeLocker.backup_manager import BackupManager
from TimeLocker.completion import (
    repository_name_completer,
    repository_completer,
    repository_uri_completer
)
from TimeLocker.utils.repository_resolver import (
    validate_repository_name_or_uri,
    resolve_repository_uri
)
from TimeLocker.cli_helpers import store_backend_credentials as store_backend_credentials_helper
from urllib.parse import urlparse
import re''',
        
        "config": '''# Configuration management
from TimeLocker.config import (
    ConfigurationModule,
    ConfigurationValidator
)
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.config.configuration_backup_manager import (
    ConfigurationBackupManager,
    BackupReason
)
from TimeLocker.config.configuration_path_resolver import ConfigurationPathResolver
from TimeLocker.importers.timeshift_importer import (
    TimeshiftConfigParser,
    TimeshiftToTimeLockerMapper
)
from TimeLocker.interfaces.exceptions import ConfigurationError
from datetime import datetime
import json
from difflib import unified_diff'''
    }
    
    return imports.get(module_name, "# TODO: Add module-specific imports")


def generate_module_header(module_info: ModuleInfo) -> str:
    """Generate the header for a command module."""
    module_imports = get_module_specific_imports(module_info.name)
    
    return f'''"""
{module_info.description.capitalize()}.

This module contains CLI commands for {module_info.description.lower()}.
Extracted from cli.py using automation script.
"""

import sys
import logging
from typing import Optional, List, Annotated, Dict, Any
from pathlib import Path

import typer
import click
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Import from base module (Phase 3 patterns)
from .base import (
    CommandBase,
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    _get_service_method,
    _call_service_method,
    _get_service_manager_for_command,
    _create_configuration_module,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
)

# Import from TimeLocker package
from TimeLocker import cli as _cli_module
from TimeLocker.cli_services import get_cli_service_manager

# Module-specific imports
{module_imports}

# Create Typer app
{module_info.app_name} = create_typer_app(
    name="{module_info.name}",
    help_text="{module_info.description}"
)


'''


def extract_command_code(cli_file: Path, command: CommandInfo) -> str:
    """Extract the code for a specific command."""
    with open(cli_file, 'r') as f:
        lines = f.readlines()
    
    command_lines = lines[command.start_line:command.end_line]
    return ''.join(command_lines)


def add_phase3_decorators(command_code: str, command_name: str) -> str:
    """
    Add Phase 3 decorators to command code.
    
    Adds @with_error_handling and @with_logging decorators.
    """
    lines = command_code.split('\n')
    
    # Find the @app.command line
    decorator_index = -1
    for i, line in enumerate(lines):
        if '.command(' in line:
            decorator_index = i
            break
    
    if decorator_index == -1:
        return command_code
    
    # Insert Phase 3 decorators after the @app.command line
    error_title = f"{command_name.replace('_', ' ').title()} Error"
    phase3_decorators = [
        f'@with_error_handling("{error_title}")',
        '@with_logging'
    ]
    
    # Insert decorators
    for decorator in reversed(phase3_decorators):
        lines.insert(decorator_index + 1, decorator)
    
    return '\n'.join(lines)


def simplify_type_annotations(command_code: str) -> str:
    """
    Replace verbose type annotations with Phase 3 aliases.
    
    Examples:
        Annotated[bool, typer.Option("--verbose", "-v", ...)] -> VerboseOption
        Annotated[bool, typer.Option("--json", ...)] -> JsonOption
    """
    replacements = {
        r'Annotated\[bool,\s*typer\.Option\("--verbose",\s*"-v"[^]]*\]\s*=\s*False':
            'VerboseOption = False',
        r'Annotated\[bool,\s*typer\.Option\("--json"[^]]*\]\s*=\s*False':
            'JsonOption = False',
        r'Annotated\[bool,\s*typer\.Option\("--yes",\s*"-y"[^]]*\]\s*=\s*False':
            'YesOption = False',
        r'Annotated\[Optional\[Path\],\s*typer\.Option\("--config-dir"[^]]*\]\s*=\s*None':
            'ConfigDirOption = None',
        r'Annotated\[bool,\s*typer\.Option\("--dry-run"[^]]*\]\s*=\s*False':
            'DryRunOption = False',
    }
    
    result = command_code
    for pattern, replacement in replacements.items():
        result = re.sub(pattern, replacement, result)
    
    return result


def extract_module(
    module_name: str,
    cli_file: Path,
    output_dir: Path,
    apply_phase3: bool = True
) -> bool:
    """
    Extract a complete module from cli.py.
    
    Args:
        module_name: Name of the module to extract
        cli_file: Path to cli.py
        output_dir: Output directory for the module
        apply_phase3: Whether to apply Phase 3 patterns
        
    Returns:
        True if successful
    """
    if module_name not in MODULES:
        print(f"❌ Unknown module: {module_name}")
        print(f"Available modules: {', '.join(MODULES.keys())}")
        return False
    
    module_info = MODULES[module_name]
    
    print(f"\n📦 Extracting module: {module_name}")
    print(f"   App name: {module_info.app_name}")
    print(f"   Description: {module_info.description}")
    
    # Find commands
    print(f"   Finding commands...")
    commands = find_commands_in_cli(cli_file, module_info.app_name)
    
    if not commands:
        print(f"   ⚠️  No commands found for {module_info.app_name}")
        return False
    
    print(f"   ✓ Found {len(commands)} commands")
    for cmd in commands:
        print(f"     - {cmd.name} ({cmd.function_name})")
    
    # Generate module file
    output_file = output_dir / f"{module_name}.py"
    print(f"   Creating {output_file}...")
    
    with open(output_file, 'w') as f:
        # Write header
        f.write(generate_module_header(module_info))
        f.write("\n# Commands\n\n")
        
        # Write each command
        for i, command in enumerate(commands):
            if i > 0:
                f.write("\n\n")
            
            # Extract command code
            command_code = extract_command_code(cli_file, command)
            
            if apply_phase3:
                # Add Phase 3 decorators
                command_code = add_phase3_decorators(command_code, command.name)
                # Simplify type annotations
                command_code = simplify_type_annotations(command_code)
            
            f.write(command_code)
    
    print(f"   ✓ Created {output_file}")
    print(f"   📊 {len(commands)} commands, ~{sum(cmd.end_line - cmd.start_line for cmd in commands)} lines")
    
    return True


def update_commands_init(output_dir: Path, module_names: List[str]):
    """Update commands/__init__.py to export new modules."""
    init_file = output_dir / "__init__.py"
    
    print(f"\n📝 Updating {init_file}...")
    
    # Read existing content
    if init_file.exists():
        with open(init_file, 'r') as f:
            content = f.read()
    else:
        content = '"""CLI command modules."""\n\n'
    
    # Add imports for new modules
    imports = []
    exports = []
    
    for module_name in module_names:
        if module_name in MODULES:
            app_name = MODULES[module_name].app_name
            import_line = f"from .{module_name} import {app_name}"
            if import_line not in content:
                imports.append(import_line)
                exports.append(app_name)
    
    if imports:
        # Add imports
        import_section = '\n'.join(imports) + '\n'
        
        # Update __all__
        if '__all__' in content:
            # Add to existing __all__
            for export in exports:
                if export not in content:
                    content = content.replace('__all__ = [', f'__all__ = [\n    "{export}",')
        else:
            # Create __all__
            export_list = ', '.join(f'"{e}"' for e in exports)
            import_section += f'\n__all__ = [{export_list}]\n'
        
        # Append imports
        content += '\n' + import_section
        
        with open(init_file, 'w') as f:
            f.write(content)
        
        print(f"   ✓ Added {len(imports)} imports")
    else:
        print(f"   ℹ️  No updates needed")


def list_modules():
    """List all available modules to extract."""
    print("\n📋 Available modules for extraction:\n")
    
    for module_name, info in sorted(MODULES.items(), key=lambda x: x[1].priority):
        print(f"  {info.priority}. {module_name}")
        print(f"     App: {info.app_name}")
        print(f"     Description: {info.description}")
        print(f"     Estimated lines: ~{info.estimated_lines}")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract CLI command modules from cli.py"
    )
    parser.add_argument(
        '--module',
        choices=list(MODULES.keys()) + ['all'],
        help='Module to extract (or "all" for all modules)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available modules'
    )
    parser.add_argument(
        '--no-phase3',
        action='store_true',
        help='Do not apply Phase 3 patterns'
    )
    parser.add_argument(
        '--cli-file',
        type=Path,
        default=Path('src/TimeLocker/cli.py'),
        help='Path to cli.py'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('src/TimeLocker/cli_modules/commands'),
        help='Output directory for modules'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_modules()
        return 0
    
    if not args.module:
        parser.print_help()
        return 1
    
    # Validate paths
    if not args.cli_file.exists():
        print(f"❌ CLI file not found: {args.cli_file}")
        return 1
    
    if not args.output_dir.exists():
        print(f"❌ Output directory not found: {args.output_dir}")
        return 1
    
    # Extract modules
    apply_phase3 = not args.no_phase3
    
    if args.module == 'all':
        modules_to_extract = sorted(MODULES.keys(), key=lambda x: MODULES[x].priority)
    else:
        modules_to_extract = [args.module]
    
    print(f"\n🚀 Starting extraction...")
    print(f"   CLI file: {args.cli_file}")
    print(f"   Output dir: {args.output_dir}")
    print(f"   Phase 3 patterns: {'enabled' if apply_phase3 else 'disabled'}")
    print(f"   Modules: {', '.join(modules_to_extract)}")
    
    success_count = 0
    extracted_modules = []
    
    for module_name in modules_to_extract:
        if extract_module(module_name, args.cli_file, args.output_dir, apply_phase3):
            success_count += 1
            extracted_modules.append(module_name)
    
    # Update __init__.py
    if extracted_modules:
        update_commands_init(args.output_dir, extracted_modules)
    
    # Summary
    print(f"\n✨ Extraction complete!")
    print(f"   ✓ {success_count}/{len(modules_to_extract)} modules extracted")
    
    if extracted_modules:
        print(f"\n📝 Next steps:")
        print(f"   1. Review generated files in {args.output_dir}")
        print(f"   2. Add missing imports (marked with TODO)")
        print(f"   3. Test imports:")
        for module in extracted_modules:
            app_name = MODULES[module].app_name
            print(f"      python -c \"from TimeLocker.cli_modules.commands import {app_name}; print('✓ {module}')\"")
        print(f"   4. Run diagnostics:")
        for module in extracted_modules:
            print(f"      # Check {module}.py")
        print(f"   5. Update REFACTORING-STATUS.md")
    
    return 0 if success_count == len(modules_to_extract) else 1


if __name__ == '__main__':
    sys.exit(main())
