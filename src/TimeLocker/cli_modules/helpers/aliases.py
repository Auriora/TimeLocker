"""
Command Aliases and Shortcuts

This module provides command alias and shortcut functionality for the TimeLocker CLI.
It enables users to use abbreviated command names and common shortcuts for frequently
used operations.

Requirements: 19.1, 19.2, 19.3
"""

from typing import Dict, List, Optional, Tuple
import difflib


class CommandAliasResolver:
    """
    Resolves command aliases and abbreviations to full command names.
    
    This class provides functionality for:
    - Command shortcuts (e.g., 'backup' -> 'backup create')
    - Command abbreviations (e.g., 'repo' -> 'repos', 'sel' -> 'selections')
    - Unambiguous prefix matching
    """
    
    # Command shortcuts - map short forms to full command paths
    SHORTCUTS: Dict[str, str] = {
        # Main command shortcuts
        "backup": "backup create",
        "restore": "restore browse",
        "repos": "repos list",
        
        # Repository shortcuts
        "repo": "repos",
        "repository": "repos",
        
        # Selection shortcuts
        "sel": "selections",
        "selection": "selections",
        
        # Policy shortcuts
        "pol": "policies",
        "policy": "policies",
        
        # Schedule shortcuts
        "sched": "schedule",
        
        # Snapshot shortcuts
        "snap": "snapshots",
        "snapshot": "snapshots",
        
        # Target shortcuts
        "tgt": "targets",
        "target": "targets",
        
        # Credential shortcuts
        "cred": "credentials",
        "credential": "credentials",
        
        # Security shortcuts
        "sec": "security",
        
        # Monitoring shortcuts
        "mon": "monitor",
        
        # Configuration shortcuts
        "cfg": "config",
        "conf": "config",
    }
    
    # Valid full command names for validation
    VALID_COMMANDS: List[str] = [
        "backup", "restore", "repos", "snapshots", "targets",
        "selections", "policies", "schedule", "credentials",
        "security", "monitor", "config", "logs", "reports",
        "notifications", "import", "export", "migrate",
        "completion", "version", "help", "status"
    ]
    
    def __init__(self):
        """Initialize the command alias resolver."""
        self._command_cache: Dict[str, str] = {}
    
    def resolve_alias(self, command: str) -> str:
        """
        Resolve a command alias or abbreviation to its full form.
        
        Args:
            command: The command string to resolve (may be abbreviated)
            
        Returns:
            The full command string
            
        Examples:
            >>> resolver = CommandAliasResolver()
            >>> resolver.resolve_alias("repo")
            'repos'
            >>> resolver.resolve_alias("sel")
            'selections'
            >>> resolver.resolve_alias("backup")
            'backup'
        """
        # Check cache first
        if command in self._command_cache:
            return self._command_cache[command]
        
        # Check if it's already a valid command
        if command in self.VALID_COMMANDS:
            self._command_cache[command] = command
            return command
        
        # Check shortcuts
        if command in self.SHORTCUTS:
            resolved = self.SHORTCUTS[command]
            self._command_cache[command] = resolved
            return resolved
        
        # Try unambiguous prefix matching
        matches = self._find_prefix_matches(command)
        if len(matches) == 1:
            resolved = matches[0]
            self._command_cache[command] = resolved
            return resolved
        
        # No match or ambiguous - return original
        return command
    
    def _find_prefix_matches(self, prefix: str) -> List[str]:
        """
        Find all commands that start with the given prefix.
        
        Args:
            prefix: The command prefix to match
            
        Returns:
            List of matching command names
        """
        prefix_lower = prefix.lower()
        matches = [
            cmd for cmd in self.VALID_COMMANDS
            if cmd.lower().startswith(prefix_lower)
        ]
        return matches
    
    def is_ambiguous(self, command: str) -> Tuple[bool, List[str]]:
        """
        Check if a command abbreviation is ambiguous.
        
        Args:
            command: The command to check
            
        Returns:
            Tuple of (is_ambiguous, list_of_matches)
            
        Examples:
            >>> resolver = CommandAliasResolver()
            >>> resolver.is_ambiguous("re")
            (True, ['repos', 'restore', 'reports'])
            >>> resolver.is_ambiguous("repo")
            (False, ['repos'])
        """
        # Check if it's a known shortcut or valid command
        if command in self.SHORTCUTS or command in self.VALID_COMMANDS:
            return False, [command]
        
        # Find prefix matches
        matches = self._find_prefix_matches(command)
        return len(matches) > 1, matches
    
    def suggest_command(self, invalid_command: str, max_suggestions: int = 3) -> List[str]:
        """
        Suggest similar valid commands for an invalid command.
        
        Args:
            invalid_command: The invalid command entered by user
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of suggested command names
            
        Examples:
            >>> resolver = CommandAliasResolver()
            >>> resolver.suggest_command("repoz")
            ['repos', 'reports']
        """
        # Use difflib to find close matches
        all_commands = list(self.VALID_COMMANDS) + list(self.SHORTCUTS.keys())
        suggestions = difflib.get_close_matches(
            invalid_command.lower(),
            [cmd.lower() for cmd in all_commands],
            n=max_suggestions,
            cutoff=0.6
        )
        
        # Map back to original case
        result = []
        for suggestion in suggestions:
            for cmd in all_commands:
                if cmd.lower() == suggestion:
                    result.append(cmd)
                    break
        
        return result
    
    def get_shortcut_help(self) -> Dict[str, str]:
        """
        Get a dictionary of all available shortcuts and their meanings.
        
        Returns:
            Dictionary mapping shortcuts to full commands
        """
        return dict(self.SHORTCUTS)
    
    def expand_command_path(self, command_path: str) -> str:
        """
        Expand a full command path with aliases.
        
        Args:
            command_path: Command path like "repo list" or "sel create"
            
        Returns:
            Expanded command path like "repos list" or "selections create"
            
        Examples:
            >>> resolver = CommandAliasResolver()
            >>> resolver.expand_command_path("repo list")
            'repos list'
            >>> resolver.expand_command_path("sel create mysel")
            'selections create mysel'
        """
        parts = command_path.split()
        if not parts:
            return command_path
        
        # Resolve the first part (main command)
        parts[0] = self.resolve_alias(parts[0])
        
        return " ".join(parts)


# Global instance for easy access
_resolver = CommandAliasResolver()


def resolve_command_alias(command: str) -> str:
    """
    Resolve a command alias to its full form.
    
    This is a convenience function that uses the global resolver instance.
    
    Args:
        command: The command to resolve
        
    Returns:
        The resolved command name
    """
    return _resolver.resolve_alias(command)


def is_command_ambiguous(command: str) -> Tuple[bool, List[str]]:
    """
    Check if a command is ambiguous.
    
    Args:
        command: The command to check
        
    Returns:
        Tuple of (is_ambiguous, list_of_matches)
    """
    return _resolver.is_ambiguous(command)


def suggest_similar_commands(invalid_command: str, max_suggestions: int = 3) -> List[str]:
    """
    Suggest similar commands for an invalid command.
    
    Args:
        invalid_command: The invalid command
        max_suggestions: Maximum number of suggestions
        
    Returns:
        List of suggested commands
    """
    return _resolver.suggest_command(invalid_command, max_suggestions)


def get_all_shortcuts() -> Dict[str, str]:
    """
    Get all available command shortcuts.
    
    Returns:
        Dictionary of shortcuts and their meanings
    """
    return _resolver.get_shortcut_help()
