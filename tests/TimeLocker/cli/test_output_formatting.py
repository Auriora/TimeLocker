"""
Tests for CLI output formatting utilities.

This module tests the JSON output, non-interactive mode, and filtering capabilities.
"""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from TimeLocker.cli_modules.helpers.output_formatter import (
    OutputFormatter,
    OutputFormat,
    ExitCode,
    create_formatter,
    format_success_json,
    format_error_json,
)
from TimeLocker.cli_modules.helpers.non_interactive import (
    require_parameter,
    validate_parameters,
    NonInteractiveError,
)
from TimeLocker.cli_modules.helpers.output_filtering import (
    OutputFilter,
    Paginator,
    create_filter,
    create_paginator,
    apply_filters_and_pagination,
    filter_sensitive_fields,
)


class TestOutputFormatter:
    """Test OutputFormatter class."""
    
    def test_create_formatter_human_mode(self):
        """Test creating formatter in human-readable mode."""
        formatter = create_formatter(json_output=False, quiet=False)
        assert formatter.format == OutputFormat.HUMAN
        assert not formatter.is_json_mode()
        assert not formatter.is_quiet_mode()
    
    def test_create_formatter_json_mode(self):
        """Test creating formatter in JSON mode."""
        formatter = create_formatter(json_output=True, quiet=False)
        assert formatter.format == OutputFormat.JSON
        assert formatter.is_json_mode()
    
    def test_create_formatter_quiet_mode(self):
        """Test creating formatter in quiet mode."""
        formatter = create_formatter(json_output=False, quiet=True)
        assert formatter.is_quiet_mode()
    
    def test_format_success_json(self):
        """Test formatting success response as JSON."""
        result = format_success_json(
            message="Operation successful",
            data={"id": "123", "name": "test"},
            command="test command"
        )
        
        data = json.loads(result)
        assert data["success"] is True
        assert data["message"] == "Operation successful"
        assert data["command"] == "test command"
        assert data["data"]["id"] == "123"
        assert "timestamp" in data
    
    def test_format_error_json(self):
        """Test formatting error response as JSON."""
        result = format_error_json(
            message="Operation failed",
            error_type="ValidationError",
            details=["Field 'name' is required"],
            code="MISSING_FIELD",
            command="test command"
        )
        
        data = json.loads(result)
        assert data["success"] is False
        assert data["error"]["message"] == "Operation failed"
        assert data["error"]["type"] == "ValidationError"
        assert data["error"]["code"] == "MISSING_FIELD"
        assert len(data["error"]["details"]) == 1


class TestNonInteractiveMode:
    """Test non-interactive mode utilities."""
    
    def test_require_parameter_with_value(self):
        """Test require_parameter when value is provided."""
        result = require_parameter("test_value", "test_param")
        assert result == "test_value"
    
    def test_require_parameter_missing_interactive(self, monkeypatch):
        """Test require_parameter with missing value in interactive mode."""
        # Mock stdin.isatty to return True (interactive)
        import sys
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        
        # Should not raise in interactive mode
        result = require_parameter(None, "test_param", allow_interactive=True)
        assert result is None
    
    def test_validate_parameters_all_present(self):
        """Test validate_parameters when all parameters are present."""
        params = {
            "name": "test",
            "value": 123,
            "flag": True
        }
        
        # Should not raise
        validate_parameters(params, allow_interactive=False)
    
    def test_validate_parameters_missing_interactive(self, monkeypatch):
        """Test validate_parameters with missing values in interactive mode."""
        import sys
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        
        params = {
            "name": "test",
            "value": None
        }
        
        # Should not raise in interactive mode
        validate_parameters(params, allow_interactive=True)


class TestOutputFiltering:
    """Test output filtering utilities."""
    
    def test_create_filter_include_fields(self):
        """Test creating filter with include fields."""
        filter = create_filter(fields="name,status,id")
        assert filter.include_fields == {"name", "status", "id"}
    
    def test_create_filter_exclude_fields(self):
        """Test creating filter with exclude fields."""
        filter = create_filter(exclude="password,secret")
        assert filter.exclude_fields == {"password", "secret"}
    
    def test_filter_dict_include(self):
        """Test filtering dictionary with include fields."""
        filter = OutputFilter(include_fields=["name", "status"])
        data = {
            "name": "test",
            "status": "active",
            "password": "secret",
            "id": "123"
        }
        
        result = filter.filter_dict(data)
        assert "name" in result
        assert "status" in result
        assert "password" not in result
        assert "id" not in result
    
    def test_filter_dict_exclude(self):
        """Test filtering dictionary with exclude fields."""
        filter = OutputFilter(exclude_fields=["password", "secret"])
        data = {
            "name": "test",
            "status": "active",
            "password": "secret",
            "id": "123"
        }
        
        result = filter.filter_dict(data)
        assert "name" in result
        assert "status" in result
        assert "id" in result
        assert "password" not in result
    
    def test_filter_list(self):
        """Test filtering list of dictionaries."""
        filter = OutputFilter(include_fields=["name", "status"])
        data = [
            {"name": "item1", "status": "active", "password": "secret1"},
            {"name": "item2", "status": "inactive", "password": "secret2"}
        ]
        
        result = filter.filter_list(data)
        assert len(result) == 2
        assert "password" not in result[0]
        assert "password" not in result[1]
    
    def test_filter_sensitive_fields(self):
        """Test filtering sensitive fields."""
        data = {
            "name": "test",
            "password": "mysecret123",
            "access_key": "AKIAIOSFODNN7EXAMPLE",
            "status": "active"
        }
        
        result = filter_sensitive_fields(data)
        assert result["name"] == "test"
        assert result["status"] == "active"
        assert "***" in result["password"]
        assert "***" in result["access_key"]
        assert "mysecret123" not in result["password"]


class TestPagination:
    """Test pagination utilities."""
    
    def test_create_paginator(self):
        """Test creating paginator."""
        paginator = create_paginator(page_size=10)
        assert paginator.page_size == 10
    
    def test_paginate_first_page(self):
        """Test paginating first page."""
        paginator = Paginator(page_size=5)
        items = list(range(20))
        
        page_items, pagination_info = paginator.paginate(items, page=1)
        
        assert len(page_items) == 5
        assert page_items == [0, 1, 2, 3, 4]
        assert pagination_info.page == 1
        assert pagination_info.total_pages == 4
        assert pagination_info.has_next is True
        assert pagination_info.has_previous is False
    
    def test_paginate_middle_page(self):
        """Test paginating middle page."""
        paginator = Paginator(page_size=5)
        items = list(range(20))
        
        page_items, pagination_info = paginator.paginate(items, page=2)
        
        assert len(page_items) == 5
        assert page_items == [5, 6, 7, 8, 9]
        assert pagination_info.page == 2
        assert pagination_info.has_next is True
        assert pagination_info.has_previous is True
    
    def test_paginate_last_page(self):
        """Test paginating last page."""
        paginator = Paginator(page_size=5)
        items = list(range(20))
        
        page_items, pagination_info = paginator.paginate(items, page=4)
        
        assert len(page_items) == 5
        assert page_items == [15, 16, 17, 18, 19]
        assert pagination_info.page == 4
        assert pagination_info.has_next is False
        assert pagination_info.has_previous is True
    
    def test_paginate_partial_last_page(self):
        """Test paginating partial last page."""
        paginator = Paginator(page_size=5)
        items = list(range(18))
        
        page_items, pagination_info = paginator.paginate(items, page=4)
        
        assert len(page_items) == 3
        assert page_items == [15, 16, 17]
        assert pagination_info.total_pages == 4
    
    def test_apply_filters_and_pagination(self):
        """Test applying both filtering and pagination."""
        data = [
            {"name": "item1", "status": "active", "password": "secret1"},
            {"name": "item2", "status": "inactive", "password": "secret2"},
            {"name": "item3", "status": "active", "password": "secret3"},
            {"name": "item4", "status": "inactive", "password": "secret4"},
            {"name": "item5", "status": "active", "password": "secret5"},
        ]
        
        filter = OutputFilter(include_fields=["name", "status"])
        paginator = Paginator(page_size=2)
        
        result = apply_filters_and_pagination(
            data=data,
            filter=filter,
            paginator=paginator,
            page=2
        )
        
        assert len(result["items"]) == 2
        assert "password" not in result["items"][0]
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["total_pages"] == 3


class TestExitCodes:
    """Test exit code constants."""
    
    def test_exit_code_values(self):
        """Test exit code enum values."""
        assert ExitCode.SUCCESS.value == 0
        assert ExitCode.WARNING.value == 1
        assert ExitCode.ERROR.value == 2
        assert ExitCode.VALIDATION_ERROR.value == 2
        assert ExitCode.OPERATION_ERROR.value == 1
        assert ExitCode.CANCELLED.value == 130
