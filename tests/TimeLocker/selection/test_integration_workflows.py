"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import pytest
import tempfile
import uuid
from pathlib import Path
from datetime import datetime

from src.TimeLocker.selection_manager import SelectionManager
from src.TimeLocker.selection_template_manager import SelectionTemplateManager
from src.TimeLocker.pattern_engine import PatternEngine
from src.TimeLocker.selection_validation_service import SelectionValidationService
from src.TimeLocker.selection_performance_optimizer import SelectionPerformanceOptimizer
from src.TimeLocker.selection_models import (
    SelectionTemplate,
    SelectionConfig,
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig,
    PrecedenceStrategy
)


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        
        # Create test file structure
        (test_dir / "documents").mkdir()
        (test_dir / "documents" / "file1.txt").write_text("content1")
        (test_dir / "documents" / "file2.doc").write_text("content2")
        (test_dir / "documents" / "report.pdf").write_text("content3")
        
        (test_dir / "temp").mkdir()
        (test_dir / "temp" / "cache.tmp").write_text("temp1")
        (test_dir / "temp" / "data.txt").write_text("temp2")
        
        (test_dir / "code").mkdir()
        (test_dir / "code" / "main.py").write_text("print('hello')")
        (test_dir / "code" / "test.py").write_text("test code")
        (test_dir / "code" / "README.md").write_text("readme")
        
        yield test_dir


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for template storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def selection_manager(temp_storage_dir):
    """Create a SelectionManager instance for testing."""
    template_manager = SelectionTemplateManager(storage_dir=temp_storage_dir)
    pattern_engine = PatternEngine()
    validation_service = SelectionValidationService(pattern_engine=pattern_engine)
    performance_optimizer = SelectionPerformanceOptimizer(pattern_engine=pattern_engine)
    
    return SelectionManager(
        template_manager=template_manager,
        pattern_engine=pattern_engine,
        validation_service=validation_service,
        performance_optimizer=performance_optimizer
    )


class TestEndToEndSelectionWorkflows:
    """Integration tests for end-to-end selection creation and evaluation workflows."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_and_evaluate_simple_selection(self, selection_manager, temp_test_dir):
        """Test creating and evaluating a simple selection."""
        # Create selection configuration
        config = SelectionConfig(
            include_paths=[temp_test_dir / "documents"],
            exclude_paths=[],
            include_patterns=[],
            exclude_patterns=[],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        # Create selection
        selection = await selection_manager.create_selection(config)
        assert selection is not None
        assert selection.config == config
        
        # Evaluate selection
        result = await selection_manager.evaluate_selection(
            selection,
            [temp_test_dir / "documents"]
        )
        
        # Verify results
        assert len(result.included_paths) == 3  # file1.txt, file2.doc, report.pdf
        assert len(result.excluded_paths) == 0
        assert result.evaluation_stats.files_evaluated == 3
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_and_evaluate_with_patterns(self, selection_manager, temp_test_dir):
        """Test creating and evaluating selection with pattern matching."""
        # Create selection with patterns
        config = SelectionConfig(
            include_paths=[temp_test_dir],
            exclude_paths=[],
            include_patterns=[
                PatternRule(
                    pattern="*.txt",
                    syntax=PatternSyntax.GLOB,
                    case_sensitive=False,
                    applies_to=PathComponent.FILENAME
                )
            ],
            exclude_patterns=[
                PatternRule(
                    pattern="*.tmp",
                    syntax=PatternSyntax.GLOB,
                    case_sensitive=False,
                    applies_to=PathComponent.FILENAME
                )
            ],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        # Create and evaluate
        selection = await selection_manager.create_selection(config)
        result = await selection_manager.evaluate_selection(selection, [temp_test_dir])
        
        # Verify .txt files are included but not .tmp files
        txt_files = [p for p in result.included_paths if p.suffix == '.txt']
        tmp_files = [p for p in result.included_paths if p.suffix == '.tmp']
        
        assert len(txt_files) >= 2  # file1.txt, data.txt
        assert len(tmp_files) == 0  # cache.tmp should be excluded
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_evaluate_and_estimate_size(self, selection_manager, temp_test_dir):
        """Test complete workflow: create, evaluate, and estimate size."""
        # Create selection
        config = SelectionConfig(
            include_paths=[temp_test_dir / "documents"],
            exclude_paths=[],
            include_patterns=[],
            exclude_patterns=[],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        selection = await selection_manager.create_selection(config)
        
        # Estimate size
        estimate = await selection_manager.estimate_selection_size(
            selection,
            [temp_test_dir / "documents"]
        )
        
        # Verify estimate
        assert estimate.file_count == 3
        assert estimate.total_size_bytes > 0
        assert estimate.estimation_accuracy >= 0.9
        assert len(estimate.inaccessible_paths) == 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_evaluate_and_preview(self, selection_manager, temp_test_dir):
        """Test complete workflow: create, evaluate, and generate preview."""
        # Create selection
        config = SelectionConfig(
            include_paths=[temp_test_dir],
            exclude_paths=[],
            include_patterns=[],
            exclude_patterns=[],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        selection = await selection_manager.create_selection(config)
        
        # Generate preview
        preview = await selection_manager.preview_selection(
            selection,
            [temp_test_dir],
            limit=5
        )
        
        # Verify preview
        assert len(preview.sample_included_files) <= 5
        assert preview.total_estimated_files > 0
        assert preview.preview_generation_time > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_hierarchical_selection_workflow(self, selection_manager, temp_test_dir):
        """Test hierarchical selection: include dir, exclude subdir, re-include specific files."""
        # Create hierarchical selection
        config = SelectionConfig(
            include_paths=[temp_test_dir],
            exclude_paths=[temp_test_dir / "temp"],
            include_patterns=[
                PatternRule(
                    pattern="data.txt",
                    syntax=PatternSyntax.LITERAL,
                    case_sensitive=False,
                    applies_to=PathComponent.FILENAME,
                    priority=300
                )
            ],
            exclude_patterns=[],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(
                default_strategy=PrecedenceStrategy.LAYERED_EVALUATION
            ),
            case_sensitive=False
        )
        
        selection = await selection_manager.create_selection(config)
        result = await selection_manager.evaluate_selection(selection, [temp_test_dir])
        
        # Verify temp directory is excluded
        temp_files = [p for p in result.included_paths if "temp" in str(p)]
        assert len(temp_files) == 0  # All temp files should be excluded
        
        # Verify other files are included
        doc_files = [p for p in result.included_paths if "documents" in str(p)]
        code_files = [p for p in result.included_paths if "code" in str(p)]
        assert len(doc_files) > 0
        assert len(code_files) > 0


class TestTemplateImportExportWorkflows:
    """Integration tests for template import/export functionality."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_export_and_import_template(self, selection_manager, temp_storage_dir):
        """Test complete template lifecycle: create, export, import."""
        # Create template
        template = SelectionTemplate(
            id=str(uuid.uuid4()),
            name="Test Export Template",
            description="Template for export testing",
            selection_config=SelectionConfig(
                include_paths=[Path("/home/user/documents")],
                exclude_paths=[],
                include_patterns=[
                    PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB)
                ],
                exclude_patterns=[],
                pattern_groups=["office_documents"],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=["test", "export"],
            usage_count=0,
            is_system_template=False
        )
        
        # Save template
        template_id = await selection_manager.template_manager.create_template(template)
        assert template_id == template.id
        
        # Export template
        export_path = temp_storage_dir / "exported_template.json"
        result_path = await selection_manager.template_manager.export_template(
            template_id,
            export_path,
            format='json'
        )
        assert result_path.exists()
        
        # Clear cache and import
        selection_manager.template_manager.templates_cache.clear()
        
        import_result = await selection_manager.template_manager.import_template(
            export_path,
            merge_strategy='skip'
        )
        
        # Verify import
        assert import_result.success
        assert import_result.imported_count == 1
        assert template_id in selection_manager.template_manager.templates_cache
        
        # Verify imported template matches original
        imported = await selection_manager.template_manager.get_template(template_id)
        assert imported.name == template.name
        assert imported.description == template.description

    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_export_multiple_templates_and_import(self, selection_manager, temp_storage_dir):
        """Test exporting and importing multiple templates."""
        # Create multiple templates
        templates = []
        for i in range(3):
            template = SelectionTemplate(
                id=str(uuid.uuid4()),
                name=f"Template {i+1}",
                description=f"Test template {i+1}",
                selection_config=SelectionConfig(
                    include_paths=[Path(f"/path{i+1}")],
                    exclude_paths=[],
                    include_patterns=[],
                    exclude_patterns=[],
                    pattern_groups=[],
                    precedence_config=PrecedenceConfig(),
                    case_sensitive=False
                ),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                tags=[f"test{i+1}"],
                is_system_template=False
            )
            templates.append(template)
            await selection_manager.template_manager.create_template(template)
        
        # Export all templates
        export_path = temp_storage_dir / "all_templates.json"
        template_ids = [t.id for t in templates]
        await selection_manager.template_manager.export_templates(
            template_ids,
            export_path,
            format='json'
        )
        assert export_path.exists()
        
        # Clear cache and import
        selection_manager.template_manager.templates_cache.clear()
        
        import_result = await selection_manager.template_manager.import_template(
            export_path,
            merge_strategy='skip'
        )
        
        # Verify all templates imported
        assert import_result.success
        assert import_result.imported_count == 3
        for template_id in template_ids:
            assert template_id in selection_manager.template_manager.templates_cache
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_template_with_selection_workflow(self, selection_manager, temp_test_dir, temp_storage_dir):
        """Test using a template in a complete selection workflow."""
        # Create and save template
        template = SelectionTemplate(
            id=str(uuid.uuid4()),
            name="Documents Template",
            description="Template for document selection",
            selection_config=SelectionConfig(
                include_paths=[temp_test_dir / "documents"],
                exclude_paths=[],
                include_patterns=[
                    PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
                    PatternRule(pattern="*.pdf", syntax=PatternSyntax.GLOB)
                ],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=["documents"],
            is_system_template=False
        )
        
        await selection_manager.template_manager.create_template(template)
        
        # Retrieve template and create selection
        retrieved_template = await selection_manager.template_manager.get_template(template.id)
        selection = await selection_manager.create_selection(retrieved_template.selection_config)
        
        # Evaluate selection
        result = await selection_manager.evaluate_selection(
            selection,
            [temp_test_dir / "documents"]
        )
        
        # Verify results - all files in documents directory are included by default
        # because include_paths includes the directory
        included_files = [p.name for p in result.included_paths]
        assert "file1.txt" in included_files
        assert "report.pdf" in included_files
        # file2.doc is also included because it's in the include_paths directory
        assert len(included_files) == 3
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_import_with_merge_strategies(self, selection_manager, temp_storage_dir):
        """Test different merge strategies during import."""
        # Create original template
        template = SelectionTemplate(
            id=str(uuid.uuid4()),
            name="Original Template",
            description="Original description",
            selection_config=SelectionConfig(
                include_paths=[Path("/original")],
                exclude_paths=[],
                include_patterns=[],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=["original"],
            is_system_template=False
        )
        
        await selection_manager.template_manager.create_template(template)
        
        # Export template
        export_path = temp_storage_dir / "template_for_merge.json"
        await selection_manager.template_manager.export_template(
            template.id,
            export_path
        )
        
        # Modify template locally
        await selection_manager.template_manager.update_template(
            template.id,
            {'description': 'Modified locally'}
        )
        
        # Test skip strategy
        result_skip = await selection_manager.template_manager.import_template(
            export_path,
            merge_strategy='skip'
        )
        assert result_skip.skipped_count == 1
        assert result_skip.imported_count == 0
        
        # Verify local changes preserved
        current = await selection_manager.template_manager.get_template(template.id)
        assert current.description == 'Modified locally'
        
        # Test overwrite strategy
        result_overwrite = await selection_manager.template_manager.import_template(
            export_path,
            merge_strategy='overwrite'
        )
        assert result_overwrite.imported_count == 1
        
        # Verify overwritten
        current = await selection_manager.template_manager.get_template(template.id)
        assert current.description == 'Original description'
        
        # Test rename strategy
        result_rename = await selection_manager.template_manager.import_template(
            export_path,
            merge_strategy='rename'
        )
        assert result_rename.imported_count == 1
        
        # Should have two templates now
        templates = await selection_manager.template_manager.list_templates()
        assert len(templates) == 2


class TestPerformanceOptimizationWorkflows:
    """Integration tests for performance optimization under load."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_optimize_selection_for_large_dataset(self, selection_manager, temp_test_dir):
        """Test optimizing selection for large file counts."""
        # Create selection with multiple patterns
        config = SelectionConfig(
            include_paths=[temp_test_dir],
            exclude_paths=[],
            include_patterns=[
                PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB, priority=100),
                PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB, priority=100),
                PatternRule(pattern="*.md", syntax=PatternSyntax.GLOB, priority=100)
            ],
            exclude_patterns=[
                PatternRule(pattern="*.tmp", syntax=PatternSyntax.GLOB, priority=100),
                PatternRule(pattern="*.cache", syntax=PatternSyntax.GLOB, priority=100)
            ],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        selection = await selection_manager.create_selection(config)
        
        # Optimize for large dataset
        optimized = await selection_manager.optimize_selection_for_performance(
            selection,
            estimated_file_count=100000
        )
        
        # Verify optimization applied
        assert optimized is not None
        assert len(optimized.optimization_applied) > 0
        assert optimized.estimated_performance_gain > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_evaluate_with_performance_monitoring(self, selection_manager, temp_test_dir):
        """Test evaluation with performance metrics."""
        # Create selection
        config = SelectionConfig(
            include_paths=[temp_test_dir],
            exclude_paths=[],
            include_patterns=[],
            exclude_patterns=[],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        selection = await selection_manager.create_selection(config)
        
        # Evaluate and check performance metrics
        result = await selection_manager.evaluate_selection(selection, [temp_test_dir])
        
        # Verify performance metrics exist
        assert result.performance_metrics is not None
        assert result.performance_metrics.files_per_second > 0
        assert result.performance_metrics.evaluation_time_ms > 0
        assert result.evaluation_stats.evaluation_time_seconds > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pattern_caching_performance(self, selection_manager, temp_test_dir):
        """Test that pattern caching improves performance."""
        # Create selection with patterns
        config = SelectionConfig(
            include_paths=[temp_test_dir],
            exclude_paths=[],
            include_patterns=[
                PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
                PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB)
            ],
            exclude_patterns=[],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        # First evaluation
        selection1 = await selection_manager.create_selection(config)
        result1 = await selection_manager.evaluate_selection(selection1, [temp_test_dir])
        time1 = result1.evaluation_stats.evaluation_time_seconds
        
        # Second evaluation with same patterns (should use cache)
        selection2 = await selection_manager.create_selection(config)
        result2 = await selection_manager.evaluate_selection(selection2, [temp_test_dir])
        time2 = result2.evaluation_stats.evaluation_time_seconds
        
        # Verify cache statistics
        cache_stats = selection_manager.pattern_engine.get_cache_statistics()
        assert cache_stats['cache_hits'] > 0
        
        # Both evaluations should complete successfully
        assert result1.evaluation_stats.files_evaluated > 0
        assert result2.evaluation_stats.files_evaluated > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_evaluations(self, selection_manager, temp_test_dir):
        """Test multiple concurrent selection evaluations."""
        import asyncio
        
        # Create different selections
        configs = [
            SelectionConfig(
                include_paths=[temp_test_dir / "documents"],
                exclude_paths=[],
                include_patterns=[],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            ),
            SelectionConfig(
                include_paths=[temp_test_dir / "code"],
                exclude_paths=[],
                include_patterns=[],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            ),
            SelectionConfig(
                include_paths=[temp_test_dir],
                exclude_paths=[temp_test_dir / "temp"],
                include_patterns=[],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            )
        ]
        
        # Create selections
        selections = []
        for config in configs:
            selection = await selection_manager.create_selection(config)
            selections.append(selection)
        
        # Evaluate concurrently
        tasks = [
            selection_manager.evaluate_selection(sel, [sel.config.include_paths[0]])
            for sel in selections
        ]
        results = await asyncio.gather(*tasks)
        
        # Verify all evaluations completed
        assert len(results) == 3
        for result in results:
            assert result.evaluation_stats.files_evaluated > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, selection_manager, temp_test_dir):
        """Test that manager tracks statistics correctly."""
        # Get initial statistics
        initial_stats = selection_manager.get_statistics()
        initial_selections = initial_stats['selections_created']
        initial_evaluations = initial_stats['evaluations_performed']
        
        # Perform operations
        config = SelectionConfig(
            include_paths=[temp_test_dir],
            exclude_paths=[],
            include_patterns=[],
            exclude_patterns=[],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        selection = await selection_manager.create_selection(config)
        await selection_manager.evaluate_selection(selection, [temp_test_dir])
        await selection_manager.validate_selection(selection)
        
        # Get updated statistics
        final_stats = selection_manager.get_statistics()
        
        # Verify statistics updated
        assert final_stats['selections_created'] > initial_selections
        assert final_stats['evaluations_performed'] > initial_evaluations
        assert final_stats['validations_performed'] > 0
        assert final_stats['total_files_evaluated'] > 0
