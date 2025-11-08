"""
Tests for interactive mode and configuration branching functionality.

This module tests the interactive prompts, wizards, and configuration branching
features added to the CLI.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from TimeLocker.cli_modules.helpers.interactive import (
    is_interactive,
    prompt_for_value,
    prompt_for_int,
    prompt_for_bool,
    validate_repository_name,
    validate_uri,
    ValidationError
)

from TimeLocker.cli_modules.helpers.wizards import (
    WizardCancelled,
)

from TimeLocker.cli_modules.helpers.command_integration import (
    with_interactive_fallback,
    ensure_repository_exists,
    prompt_for_missing_parameters,
)


class TestInteractiveMode:
    """Test interactive mode detection and prompts."""
    
    def test_is_interactive_with_tty(self):
        """Test interactive mode detection with TTY."""
        with patch('sys.stdin.isatty', return_value=True):
            assert is_interactive() is True
    
    def test_is_interactive_without_tty(self):
        """Test interactive mode detection without TTY."""
        with patch('sys.stdin.isatty', return_value=False):
            assert is_interactive() is False
    
    def test_validate_repository_name_valid(self):
        """Test repository name validation with valid names."""
        assert validate_repository_name("myrepo") is True
        assert validate_repository_name("my-repo") is True
        assert validate_repository_name("my_repo") is True
        assert validate_repository_name("my.repo") is True
        assert validate_repository_name("repo123") is True
    
    def test_validate_repository_name_invalid(self):
        """Test repository name validation with invalid names."""
        assert validate_repository_name("") is False
        assert validate_repository_name("   ") is False
        assert validate_repository_name("my repo") is False
        assert validate_repository_name("my@repo") is False
        assert validate_repository_name("my/repo") is False
    
    def test_validate_uri_valid(self):
        """Test URI validation with valid URIs."""
        assert validate_uri("file:///path/to/repo") is True
        assert validate_uri("s3://bucket/path") is True
        assert validate_uri("b2://bucket") is True
        assert validate_uri("/absolute/path") is True
    
    def test_validate_uri_invalid(self):
        """Test URI validation with invalid URIs."""
        assert validate_uri("") is False
        assert validate_uri("   ") is False
        assert validate_uri("invalid") is False
        assert validate_uri("http://example.com") is False


class TestPromptForValue:
    """Test prompt_for_value function."""
    
    def test_prompt_in_non_interactive_mode_with_default(self):
        """Test prompt returns default in non-interactive mode."""
        with patch('sys.stdin.isatty', return_value=False):
            result = prompt_for_value(
                "Test prompt",
                default="default_value",
                required=False
            )
            assert result == "default_value"
    
    def test_prompt_in_non_interactive_mode_required_raises(self):
        """Test prompt raises error for required value in non-interactive mode."""
        with patch('sys.stdin.isatty', return_value=False):
            with pytest.raises(ValidationError):
                prompt_for_value(
                    "Test prompt",
                    required=True
                )
    
    def test_prompt_with_current_value_in_non_interactive(self):
        """Test prompt returns current value in non-interactive mode."""
        with patch('sys.stdin.isatty', return_value=False):
            result = prompt_for_value(
                "Test prompt",
                current_value="current",
                required=True
            )
            assert result == "current"


class TestPromptForInt:
    """Test prompt_for_int function."""
    
    def test_prompt_int_in_non_interactive_mode_with_default(self):
        """Test integer prompt returns default in non-interactive mode."""
        with patch('sys.stdin.isatty', return_value=False):
            result = prompt_for_int(
                "Test prompt",
                default=42,
                required=False
            )
            assert result == 42
    
    def test_prompt_int_in_non_interactive_mode_required_raises(self):
        """Test integer prompt raises error for required value in non-interactive mode."""
        with patch('sys.stdin.isatty', return_value=False):
            with pytest.raises(ValidationError):
                prompt_for_int(
                    "Test prompt",
                    required=True
                )


class TestPromptForBool:
    """Test prompt_for_bool function."""
    
    def test_prompt_bool_in_non_interactive_mode_with_default(self):
        """Test boolean prompt returns default in non-interactive mode."""
        with patch('sys.stdin.isatty', return_value=False):
            result = prompt_for_bool(
                "Test prompt",
                default=True
            )
            assert result is True
    
    def test_prompt_bool_with_current_value_in_non_interactive(self):
        """Test boolean prompt returns current value in non-interactive mode."""
        with patch('sys.stdin.isatty', return_value=False):
            result = prompt_for_bool(
                "Test prompt",
                current_value=False
            )
            assert result is False


class TestCommandIntegration:
    """Test command integration utilities."""
    
    def test_with_interactive_fallback_all_params_provided(self):
        """Test fallback returns params when all are provided."""
        mock_wizard = Mock()
        mock_config = Mock()
        
        result = with_interactive_fallback(
            wizard_func=mock_wizard,
            required_params={"name": "test", "uri": "file:///test"},
            config_module=mock_config
        )
        
        assert result == {"name": "test", "uri": "file:///test"}
        mock_wizard.assert_not_called()
    
    def test_with_interactive_fallback_missing_params_non_interactive(self):
        """Test fallback raises error for missing params in non-interactive mode."""
        mock_wizard = Mock()
        mock_config = Mock()
        
        with patch('sys.stdin.isatty', return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                with_interactive_fallback(
                    wizard_func=mock_wizard,
                    required_params={"name": None, "uri": "file:///test"},
                    config_module=mock_config
                )
            
            assert "name" in str(exc_info.value)
    
    def test_ensure_repository_exists_with_existing_repo(self):
        """Test ensure_repository_exists with existing repository."""
        mock_config = Mock()
        mock_config.get_repository.return_value = Mock(name="test-repo")
        
        result = ensure_repository_exists(
            repository_name="test-repo",
            config_module=mock_config,
            allow_creation=False
        )
        
        assert result == "test-repo"
        mock_config.get_repository.assert_called_once_with("test-repo")
    
    def test_ensure_repository_exists_missing_non_interactive_raises(self):
        """Test ensure_repository_exists raises error for missing repo in non-interactive mode."""
        mock_config = Mock()
        mock_config.get_repository.side_effect = Exception("Not found")
        
        with patch('sys.stdin.isatty', return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                ensure_repository_exists(
                    repository_name="missing-repo",
                    config_module=mock_config,
                    allow_creation=False
                )
            
            assert "missing-repo" in str(exc_info.value)
    
    def test_prompt_for_missing_parameters_all_provided(self):
        """Test prompt_for_missing_parameters with all params provided."""
        result = prompt_for_missing_parameters(
            command_name="test",
            parameters={"name": "test", "value": "123"},
            parameter_prompts={"name": "Name", "value": "Value"}
        )
        
        assert result == {"name": "test", "value": "123"}
    
    def test_prompt_for_missing_parameters_missing_non_interactive_raises(self):
        """Test prompt_for_missing_parameters raises error in non-interactive mode."""
        with patch('sys.stdin.isatty', return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                prompt_for_missing_parameters(
                    command_name="test",
                    parameters={"name": None},
                    parameter_prompts={"name": "Name"}
                )
            
            assert "name" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
