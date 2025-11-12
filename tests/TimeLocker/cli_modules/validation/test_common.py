"""Tests for common validators."""

import pytest
import tempfile
from pathlib import Path
from TimeLocker.cli_modules.validation.common import (
    PathValidator,
    NameValidator,
    EmailValidator,
    URLValidator,
    PortValidator,
    CronValidator,
    IntegerRangeValidator,
    StringLengthValidator,
    RegexValidator,
)


class TestPathValidator:
    """Tests for PathValidator."""
    
    def test_valid_path(self):
        """Test validation of valid path."""
        validator = PathValidator()
        result = validator.validate("/tmp")
        assert result.valid is True
    
    def test_empty_path(self):
        """Test validation of empty path."""
        validator = PathValidator()
        result = validator.validate("")
        assert result.valid is False
        assert any("empty" in e.message.lower() for e in result.get_errors())
    
    def test_must_exist(self):
        """Test path must exist validation."""
        validator = PathValidator(must_exist=True)
        
        # Existing path
        result = validator.validate("/tmp")
        assert result.valid is True
        
        # Non-existing path
        result = validator.validate("/nonexistent/path/12345")
        assert result.valid is False
        assert any("not exist" in e.message.lower() for e in result.get_errors())
    
    def test_must_not_exist(self):
        """Test path must not exist validation."""
        validator = PathValidator(must_not_exist=True)
        
        # Non-existing path
        result = validator.validate("/nonexistent/path/12345")
        assert result.valid is True
        
        # Existing path
        result = validator.validate("/tmp")
        assert result.valid is False
        assert any("already exists" in e.message.lower() for e in result.get_errors())
    
    def test_must_be_directory(self):
        """Test path must be directory validation."""
        validator = PathValidator(must_exist=True, must_be_directory=True)
        
        # Directory
        result = validator.validate("/tmp")
        assert result.valid is True
        
        # File (create temporary file)
        with tempfile.NamedTemporaryFile() as tmp:
            result = validator.validate(tmp.name)
            assert result.valid is False


class TestNameValidator:
    """Tests for NameValidator."""
    
    def test_valid_name(self):
        """Test validation of valid name."""
        validator = NameValidator()
        result = validator.validate("my-repository")
        assert result.valid is True
    
    def test_empty_name(self):
        """Test validation of empty name."""
        validator = NameValidator()
        result = validator.validate("")
        assert result.valid is False
    
    def test_min_length(self):
        """Test minimum length validation."""
        validator = NameValidator(min_length=5)
        
        result = validator.validate("ab")
        assert result.valid is False
        assert any("at least 5" in e.message for e in result.get_errors())
        
        result = validator.validate("abcde")
        assert result.valid is True
    
    def test_max_length(self):
        """Test maximum length validation."""
        validator = NameValidator(max_length=10)
        
        result = validator.validate("verylongname")
        assert result.valid is False
        assert any("at most 10" in e.message for e in result.get_errors())
        
        result = validator.validate("shortname")
        assert result.valid is True
    
    def test_spaces_not_allowed(self):
        """Test spaces not allowed validation."""
        validator = NameValidator(allow_spaces=False)
        
        result = validator.validate("my repository")
        assert result.valid is False
        assert any("spaces" in e.message.lower() for e in result.get_errors())
    
    def test_spaces_allowed(self):
        """Test spaces allowed validation."""
        validator = NameValidator(allow_spaces=True)
        
        result = validator.validate("my repository")
        assert result.valid is True
    
    def test_special_chars_not_allowed(self):
        """Test special characters not allowed validation."""
        validator = NameValidator(allow_special_chars=False)
        
        result = validator.validate("my@repository")
        assert result.valid is False
    
    def test_reserved_names(self):
        """Test reserved names validation."""
        validator = NameValidator(reserved_names={"default", "system"})
        
        result = validator.validate("default")
        assert result.valid is False
        assert any("reserved" in e.message.lower() for e in result.get_errors())
        
        result = validator.validate("myrepo")
        assert result.valid is True


class TestEmailValidator:
    """Tests for EmailValidator."""
    
    def test_valid_email(self):
        """Test validation of valid email."""
        validator = EmailValidator()
        result = validator.validate("user@example.com")
        assert result.valid is True
    
    def test_invalid_email(self):
        """Test validation of invalid email."""
        validator = EmailValidator()
        
        invalid_emails = [
            "invalid",
            "@example.com",
            "user@",
            "user@.com",
            "user example@test.com",
        ]
        
        for email in invalid_emails:
            result = validator.validate(email)
            assert result.valid is False, f"Email {email} should be invalid"
    
    def test_empty_email(self):
        """Test validation of empty email."""
        validator = EmailValidator()
        result = validator.validate("")
        assert result.valid is False


class TestURLValidator:
    """Tests for URLValidator."""
    
    def test_valid_url(self):
        """Test validation of valid URL."""
        validator = URLValidator()
        result = validator.validate("https://example.com")
        assert result.valid is True
    
    def test_missing_scheme(self):
        """Test URL without scheme."""
        validator = URLValidator(require_scheme=True)
        result = validator.validate("example.com")
        assert result.valid is False
    
    def test_allowed_schemes(self):
        """Test allowed schemes validation."""
        validator = URLValidator(allowed_schemes=["https"])
        
        result = validator.validate("https://example.com")
        assert result.valid is True
        
        result = validator.validate("http://example.com")
        assert result.valid is False


class TestPortValidator:
    """Tests for PortValidator."""
    
    def test_valid_port(self):
        """Test validation of valid port."""
        validator = PortValidator()
        result = validator.validate(8080)
        assert result.valid is True
    
    def test_port_out_of_range(self):
        """Test port out of range."""
        validator = PortValidator()
        
        result = validator.validate(0)
        assert result.valid is False
        
        result = validator.validate(70000)
        assert result.valid is False
    
    def test_invalid_port_type(self):
        """Test invalid port type."""
        validator = PortValidator()
        result = validator.validate("not a number")
        assert result.valid is False


class TestCronValidator:
    """Tests for CronValidator."""
    
    def test_valid_cron(self):
        """Test validation of valid cron expression."""
        validator = CronValidator()
        result = validator.validate("0 0 * * *")
        assert result.valid is True
    
    def test_invalid_cron(self):
        """Test validation of invalid cron expression."""
        validator = CronValidator()
        
        result = validator.validate("invalid")
        assert result.valid is False
        
        result = validator.validate("0 0 * *")  # Too few fields
        assert result.valid is False


class TestIntegerRangeValidator:
    """Tests for IntegerRangeValidator."""
    
    def test_valid_integer(self):
        """Test validation of valid integer."""
        validator = IntegerRangeValidator(min_value=0, max_value=100)
        result = validator.validate(50)
        assert result.valid is True
    
    def test_below_minimum(self):
        """Test integer below minimum."""
        validator = IntegerRangeValidator(min_value=10)
        result = validator.validate(5)
        assert result.valid is False
    
    def test_above_maximum(self):
        """Test integer above maximum."""
        validator = IntegerRangeValidator(max_value=100)
        result = validator.validate(150)
        assert result.valid is False
    
    def test_invalid_type(self):
        """Test invalid integer type."""
        validator = IntegerRangeValidator()
        result = validator.validate("not a number")
        assert result.valid is False


class TestStringLengthValidator:
    """Tests for StringLengthValidator."""
    
    def test_valid_length(self):
        """Test validation of valid string length."""
        validator = StringLengthValidator(min_length=3, max_length=10)
        result = validator.validate("hello")
        assert result.valid is True
    
    def test_too_short(self):
        """Test string too short."""
        validator = StringLengthValidator(min_length=5)
        result = validator.validate("hi")
        assert result.valid is False
    
    def test_too_long(self):
        """Test string too long."""
        validator = StringLengthValidator(max_length=5)
        result = validator.validate("verylongstring")
        assert result.valid is False


class TestRegexValidator:
    """Tests for RegexValidator."""
    
    def test_valid_pattern(self):
        """Test validation with matching pattern."""
        validator = RegexValidator(pattern=r"^[a-z]+$")
        result = validator.validate("hello")
        assert result.valid is True
    
    def test_invalid_pattern(self):
        """Test validation with non-matching pattern."""
        validator = RegexValidator(pattern=r"^[a-z]+$")
        result = validator.validate("Hello123")
        assert result.valid is False
    
    def test_custom_error_message(self):
        """Test custom error message."""
        validator = RegexValidator(
            pattern=r"^[a-z]+$",
            error_message="Must contain only lowercase letters"
        )
        result = validator.validate("Hello")
        assert result.valid is False
        assert any("lowercase" in e.message for e in result.get_errors())
