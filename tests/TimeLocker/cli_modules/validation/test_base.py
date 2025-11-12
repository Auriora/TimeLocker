"""Tests for base validation classes."""

import pytest
from TimeLocker.cli_modules.validation.base import (
    Validator,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    ValidationIssue,
    CompositeValidator,
    OptionalValidator,
    ConditionalValidator,
)


class TestValidationResult:
    """Tests for ValidationResult class."""
    
    def test_initial_state(self):
        """Test initial validation result state."""
        result = ValidationResult()
        assert result.valid is True
        assert len(result.issues) == 0
        assert len(result.metadata) == 0
    
    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult()
        result.add_error("field1", "Error message", "ERROR_CODE")
        
        assert result.valid is False
        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.ERROR
        assert result.issues[0].field == "field1"
        assert result.issues[0].message == "Error message"
        assert result.issues[0].code == "ERROR_CODE"
    
    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult()
        result.add_warning("field1", "Warning message", "WARNING_CODE")
        
        assert result.valid is True  # Warnings don't invalidate
        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.WARNING
    
    def test_add_info(self):
        """Test adding info messages."""
        result = ValidationResult()
        result.add_info("field1", "Info message", "INFO_CODE")
        
        assert result.valid is True
        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.INFO
    
    def test_merge(self):
        """Test merging validation results."""
        result1 = ValidationResult()
        result1.add_error("field1", "Error 1", "ERROR1")
        
        result2 = ValidationResult()
        result2.add_warning("field2", "Warning 1", "WARNING1")
        
        result1.merge(result2)
        
        assert result1.valid is False
        assert len(result1.issues) == 2
    
    def test_get_errors(self):
        """Test getting only errors."""
        result = ValidationResult()
        result.add_error("field1", "Error", "ERROR")
        result.add_warning("field2", "Warning", "WARNING")
        result.add_info("field3", "Info", "INFO")
        
        errors = result.get_errors()
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR
    
    def test_get_warnings(self):
        """Test getting only warnings."""
        result = ValidationResult()
        result.add_error("field1", "Error", "ERROR")
        result.add_warning("field2", "Warning", "WARNING")
        
        warnings = result.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].severity == ValidationSeverity.WARNING
    
    def test_bool_conversion(self):
        """Test boolean conversion."""
        result = ValidationResult()
        assert bool(result) is True
        
        result.add_error("field", "Error", "ERROR")
        assert bool(result) is False


class SimpleValidator(Validator):
    """Simple validator for testing."""
    
    def __init__(self, should_pass: bool = True, field_name: str = "test"):
        super().__init__(field_name)
        self.should_pass = should_pass
    
    def validate(self, value, context=None):
        result = ValidationResult()
        if not self.should_pass:
            result.add_error(self.field_name, "Validation failed", "TEST_ERROR")
        return result


class TestCompositeValidator:
    """Tests for CompositeValidator."""
    
    def test_and_logic_all_pass(self):
        """Test AND logic when all validators pass."""
        v1 = SimpleValidator(should_pass=True)
        v2 = SimpleValidator(should_pass=True)
        
        composite = CompositeValidator([v1, v2], require_all=True)
        result = composite.validate("test")
        
        assert result.valid is True
    
    def test_and_logic_one_fails(self):
        """Test AND logic when one validator fails."""
        v1 = SimpleValidator(should_pass=True)
        v2 = SimpleValidator(should_pass=False)
        
        composite = CompositeValidator([v1, v2], require_all=True)
        result = composite.validate("test")
        
        assert result.valid is False
    
    def test_or_logic_one_passes(self):
        """Test OR logic when one validator passes."""
        v1 = SimpleValidator(should_pass=True)
        v2 = SimpleValidator(should_pass=False)
        
        composite = CompositeValidator([v1, v2], require_all=False)
        result = composite.validate("test")
        
        assert result.valid is True
    
    def test_or_logic_all_fail(self):
        """Test OR logic when all validators fail."""
        v1 = SimpleValidator(should_pass=False)
        v2 = SimpleValidator(should_pass=False)
        
        composite = CompositeValidator([v1, v2], require_all=False)
        result = composite.validate("test")
        
        assert result.valid is False
    
    def test_and_operator(self):
        """Test & operator for combining validators."""
        v1 = SimpleValidator(should_pass=True)
        v2 = SimpleValidator(should_pass=True)
        
        combined = v1 & v2
        result = combined.validate("test")
        
        assert result.valid is True
        assert isinstance(combined, CompositeValidator)
    
    def test_or_operator(self):
        """Test | operator for combining validators."""
        v1 = SimpleValidator(should_pass=False)
        v2 = SimpleValidator(should_pass=True)
        
        combined = v1 | v2
        result = combined.validate("test")
        
        assert result.valid is True
        assert isinstance(combined, CompositeValidator)


class TestOptionalValidator:
    """Tests for OptionalValidator."""
    
    def test_none_value(self):
        """Test that None values pass validation."""
        inner = SimpleValidator(should_pass=False)
        validator = OptionalValidator(inner)
        
        result = validator.validate(None)
        assert result.valid is True
    
    def test_empty_string_allowed(self):
        """Test that empty strings pass when allowed."""
        inner = SimpleValidator(should_pass=False)
        validator = OptionalValidator(inner, allow_empty=True)
        
        result = validator.validate("")
        assert result.valid is True
    
    def test_empty_string_not_allowed(self):
        """Test that empty strings are validated when not allowed."""
        inner = SimpleValidator(should_pass=False)
        validator = OptionalValidator(inner, allow_empty=False)
        
        result = validator.validate("")
        assert result.valid is False
    
    def test_present_value(self):
        """Test that present values are validated."""
        inner = SimpleValidator(should_pass=False)
        validator = OptionalValidator(inner)
        
        result = validator.validate("value")
        assert result.valid is False


class TestConditionalValidator:
    """Tests for ConditionalValidator."""
    
    def test_condition_met(self):
        """Test validation when condition is met."""
        inner = SimpleValidator(should_pass=False)
        validator = ConditionalValidator(
            inner,
            condition=lambda v, c: v == "validate_me"
        )
        
        result = validator.validate("validate_me")
        assert result.valid is False
    
    def test_condition_not_met(self):
        """Test validation when condition is not met."""
        inner = SimpleValidator(should_pass=False)
        validator = ConditionalValidator(
            inner,
            condition=lambda v, c: v == "validate_me"
        )
        
        result = validator.validate("skip_me")
        assert result.valid is True
    
    def test_condition_with_context(self):
        """Test validation with context."""
        inner = SimpleValidator(should_pass=False)
        validator = ConditionalValidator(
            inner,
            condition=lambda v, c: c and c.get('validate', False)
        )
        
        result = validator.validate("value", {'validate': True})
        assert result.valid is False
        
        result = validator.validate("value", {'validate': False})
        assert result.valid is True


class TestValidationError:
    """Tests for ValidationError exception."""
    
    def test_basic_error(self):
        """Test basic validation error."""
        error = ValidationError("Test error")
        assert str(error) == "Test error"
    
    def test_error_with_result(self):
        """Test validation error with result."""
        result = ValidationResult()
        result.add_error("field1", "Error 1", "ERROR1")
        result.add_error("field2", "Error 2", "ERROR2")
        
        error = ValidationError("Validation failed", result=result)
        messages = error.get_error_messages()
        
        # Should return error messages from the result
        assert len(messages) == 2
        assert "Error 1" in messages
        assert "Error 2" in messages
        
        # Test without result
        error_no_result = ValidationError("Simple error")
        messages_no_result = error_no_result.get_error_messages()
        assert len(messages_no_result) == 1
        assert "Simple error" in messages_no_result[0]
    
    def test_error_with_field(self):
        """Test validation error with field."""
        error = ValidationError("Test error", field="test_field")
        assert error.field == "test_field"
