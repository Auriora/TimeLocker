"""
Tests for ProgressService.

This module tests the centralized progress tracking service.
"""

import pytest
from io import StringIO
from rich.console import Console
from unittest.mock import Mock

from TimeLocker.utils.progress_service import (
    ProgressService,
    ProgressContext,
    ProgressType,
    ProgressTemplates,
    get_progress_service
)


class TestProgressService:
    """Test ProgressService functionality."""
    
    def test_initialization(self):
        """Test ProgressService initialization."""
        service = ProgressService()
        assert service.is_enabled()
        assert not service.has_active_progress()
    
    def test_initialization_disabled(self):
        """Test ProgressService initialization with disabled progress."""
        service = ProgressService(enabled=False)
        assert not service.is_enabled()
    
    def test_enable_disable(self):
        """Test enabling and disabling progress tracking."""
        service = ProgressService()
        assert service.is_enabled()
        
        service.set_enabled(False)
        assert not service.is_enabled()
        
        service.set_enabled(True)
        assert service.is_enabled()
    
    def test_spinner_context(self):
        """Test spinner progress context."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with service.spinner("Testing spinner") as progress:
            assert isinstance(progress, ProgressContext)
            assert progress.description == "Testing spinner"
            assert service.has_active_progress()
        
        assert not service.has_active_progress()
    
    def test_bar_context(self):
        """Test bar progress context."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with service.bar("Testing bar", total=100) as progress:
            assert isinstance(progress, ProgressContext)
            assert progress.description == "Testing bar"
            assert progress.total == 100
            assert service.has_active_progress()
            
            # Update progress
            progress.update(advance=10)
            assert progress.completed == 10
        
        assert not service.has_active_progress()

    @pytest.mark.parametrize("context_name", ["spinner", "bar"])
    def test_body_exception_remains_primary(self, context_name):
        """Progress cleanup must not yield twice or replace the body failure."""
        output = StringIO()
        service = ProgressService(console=Console(file=output, width=80))
        context = (
            service.spinner("Failing operation")
            if context_name == "spinner"
            else service.bar("Failing operation", total=1)
        )

        with pytest.raises(ValueError, match="primary failure"):
            with context as progress:
                progress.complete = Mock(side_effect=RuntimeError("cleanup failure"))
                raise ValueError("primary failure")

        assert not service.has_active_progress()
    
    def test_simple_context(self):
        """Test simple progress context."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with service.simple("Testing simple") as progress:
            assert isinstance(progress, ProgressContext)
            assert progress.description == "Testing simple"
            assert service.has_active_progress()
        
        assert not service.has_active_progress()
    
    def test_nested_context(self):
        """Test nested progress context."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        child_descriptions = ["Step 1", "Step 2", "Step 3"]
        with service.nested("Parent task", child_descriptions) as (parent, children):
            assert isinstance(parent, ProgressContext)
            assert len(children) == 3
            assert parent.total == 3
            assert service.has_active_progress()
            
            # Complete children
            for child in children:
                assert isinstance(child, ProgressContext)
                child.complete()
                parent.update(advance=1)
        
        assert not service.has_active_progress()
    
    def test_disabled_progress(self):
        """Test that disabled progress provides no-op contexts."""
        service = ProgressService(enabled=False)
        
        with service.spinner("Testing") as progress:
            assert isinstance(progress, ProgressContext)
            # Should not raise errors when updating
            progress.update(description="Updated")
        
        with service.bar("Testing", total=100) as progress:
            assert isinstance(progress, ProgressContext)
            progress.update(advance=10)
    
    def test_progress_update(self):
        """Test progress update functionality."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with service.bar("Testing", total=100) as progress:
            progress.update(advance=25)
            assert progress.completed == 25
            
            progress.update(advance=25, description="Half done")
            assert progress.completed == 50
            assert progress.description == "Half done"
    
    def test_set_total(self):
        """Test setting total dynamically."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with service.bar("Testing", total=50) as progress:
            assert progress.total == 50
            
            progress.set_total(100)
            assert progress.total == 100
    
    def test_complete(self):
        """Test completing progress."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with service.bar("Testing", total=100) as progress:
            progress.update(advance=50)
            assert progress.completed == 50
            
            progress.complete()
            # Complete should advance to total
            assert progress.completed >= 50
    
    def test_get_active_contexts(self):
        """Test getting active contexts."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        assert len(service.get_active_contexts()) == 0
        
        with service.spinner("Testing"):
            contexts = service.get_active_contexts()
            assert len(contexts) == 1
            assert contexts[0].description == "Testing"
        
        assert len(service.get_active_contexts()) == 0


class TestProgressTemplates:
    """Test ProgressTemplates functionality."""
    
    def test_backup_operation_template(self):
        """Test backup operation template."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with ProgressTemplates.backup_operation(service, "test-repo") as progress:
            assert isinstance(progress, ProgressContext)
            assert "test-repo" in progress.description
    
    def test_restore_operation_template(self):
        """Test restore operation template."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        snapshot_id = "abc123def456"
        target = "/tmp/restore"
        
        with ProgressTemplates.restore_operation(service, snapshot_id, target) as progress:
            assert isinstance(progress, ProgressContext)
            assert snapshot_id[:12] in progress.description
            assert target in progress.description
    
    def test_repository_operation_template(self):
        """Test repository operation template."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with ProgressTemplates.repository_operation(service, "init", "test-repo") as progress:
            assert isinstance(progress, ProgressContext)
            assert "Init" in progress.description
            assert "test-repo" in progress.description
    
    def test_batch_operation_template(self):
        """Test batch operation template."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with ProgressTemplates.batch_operation(service, "Processing", 50) as progress:
            assert isinstance(progress, ProgressContext)
            assert progress.total == 50
            assert "Processing" in progress.description
    
    def test_validation_operation_template(self):
        """Test validation operation template."""
        output = StringIO()
        console = Console(file=output, width=80)
        service = ProgressService(console=console)
        
        with ProgressTemplates.validation_operation(service, "configuration") as progress:
            assert isinstance(progress, ProgressContext)
            assert "configuration" in progress.description


class TestGetProgressService:
    """Test get_progress_service singleton function."""
    
    def test_get_default_service(self):
        """Test getting default service instance."""
        service = get_progress_service()
        assert isinstance(service, ProgressService)
        assert service.is_enabled()
    
    def test_singleton_behavior(self):
        """Test that get_progress_service returns same instance."""
        service1 = get_progress_service()
        service2 = get_progress_service()
        assert service1 is service2
