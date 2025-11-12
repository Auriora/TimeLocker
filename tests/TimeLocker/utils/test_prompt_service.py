"""
Tests for PromptService.

This module tests the centralized prompt service for CLI interactive operations.
"""

import pytest
from io import StringIO
from unittest.mock import Mock, patch
from pathlib import Path

from TimeLocker.utils import PromptService, PromptError


class TestPromptService:
    """Test suite for PromptService."""
    
    def test_initialization(self):
        """Test PromptService initialization."""
        service = PromptService()
        assert service is not None
        assert service._console is not None
    
    def test_is_interactive_default(self):
        """Test interactive mode detection."""
        service = PromptService()
        # Default behavior depends on stdin.isatty()
        result = service.is_interactive()
        assert isinstance(result, bool)
    
    def test_is_interactive_forced(self):
        """Test forced interactive mode."""
        service = PromptService(force_interactive=True)
        assert service.is_interactive() is True
        
        service = PromptService(force_interactive=False)
        assert service.is_interactive() is False
    
    def test_prompt_text_non_interactive_with_default(self):
        """Test text prompt in non-interactive mode with default."""
        service = PromptService(force_interactive=False)
        result = service.prompt_text("Enter value", default="test_default")
        assert result == "test_default"
    
    def test_prompt_text_non_interactive_required_raises(self):
        """Test text prompt in non-interactive mode without default raises error."""
        service = PromptService(force_interactive=False)
        with pytest.raises(PromptError):
            service.prompt_text("Enter value", required=True)
    
    def test_prompt_text_non_interactive_not_required(self):
        """Test text prompt in non-interactive mode when not required."""
        service = PromptService(force_interactive=False)
        result = service.prompt_text("Enter value", required=False)
        assert result is None
    
    def test_prompt_choice_non_interactive_with_default(self):
        """Test choice prompt in non-interactive mode with default."""
        service = PromptService(force_interactive=False)
        result = service.prompt_choice("Select", choices=["a", "b", "c"], default="b")
        assert result == "b"
    
    def test_prompt_choice_empty_choices_raises(self):
        """Test choice prompt with empty choices raises error."""
        service = PromptService(force_interactive=False)
        with pytest.raises(ValueError):
            service.prompt_choice("Select", choices=[])
    
    def test_prompt_confirm_non_interactive_with_default(self):
        """Test confirm prompt in non-interactive mode."""
        service = PromptService(force_interactive=False)
        result = service.prompt_confirm("Confirm?", default=True)
        assert result is True
        
        result = service.prompt_confirm("Confirm?", default=False)
        assert result is False
    
    def test_prompt_password_non_interactive_raises(self):
        """Test password prompt in non-interactive mode raises error."""
        service = PromptService(force_interactive=False)
        with pytest.raises(PromptError):
            service.prompt_password("Enter password", required=True)
    
    def test_prompt_int_non_interactive_with_default(self):
        """Test integer prompt in non-interactive mode with default."""
        service = PromptService(force_interactive=False)
        result = service.prompt_int("Enter number", default=42)
        assert result == 42
    
    def test_prompt_float_non_interactive_with_default(self):
        """Test float prompt in non-interactive mode with default."""
        service = PromptService(force_interactive=False)
        result = service.prompt_float("Enter number", default=3.14)
        assert result == 3.14
    
    def test_prompt_path_non_interactive_with_default(self):
        """Test path prompt in non-interactive mode with default."""
        service = PromptService(force_interactive=False)
        default_path = Path("/tmp/test")
        result = service.prompt_path("Enter path", default=default_path)
        assert result == default_path
    
    def test_prompt_list_non_interactive_with_default(self):
        """Test list prompt in non-interactive mode with default."""
        service = PromptService(force_interactive=False)
        result = service.prompt_list("Enter items", default=["a", "b", "c"])
        assert result == ["a", "b", "c"]
    
    def test_prompt_to_change_non_interactive(self):
        """Test prompt to change in non-interactive mode."""
        service = PromptService(force_interactive=False)
        result = service.prompt_to_change("field", "current_value")
        assert result is False
    
    def test_current_value_handling(self):
        """Test that current_value is returned when appropriate."""
        service = PromptService(force_interactive=False)
        
        # Text prompt with current value
        result = service.prompt_text("Enter value", current_value="existing", required=True)
        assert result == "existing"
        
        # Int prompt with current value
        result = service.prompt_int("Enter number", current_value=99, required=True)
        assert result == 99
        
        # Confirm with current value
        result = service.prompt_confirm("Confirm?", current_value=True)
        assert result is True


class TestGetPromptService:
    """Test suite for get_prompt_service function."""
    
    def test_get_prompt_service_singleton(self):
        """Test that get_prompt_service returns singleton instance."""
        from TimeLocker.utils.prompt_service import get_prompt_service, _default_prompt_service
        
        # Reset singleton
        import TimeLocker.utils.prompt_service as ps_module
        ps_module._default_prompt_service = None
        
        service1 = get_prompt_service()
        service2 = get_prompt_service()
        
        assert service1 is service2
        assert service1 is not None
