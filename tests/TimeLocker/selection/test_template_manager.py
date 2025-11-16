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

from src.TimeLocker.selection_template_manager import (
    SelectionTemplateManager,
    TemplateNotFoundError,
    TemplateAlreadyExistsError,
    TemplateValidationError,
    TemplateImportError,
    TemplateExportError
)
from src.TimeLocker.selection_models import (
    SelectionTemplate,
    SelectionConfig,
    PatternRule,
    PatternSyntax,
    PrecedenceConfig,
    PrecedenceStrategy
)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for template storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def template_manager(temp_storage_dir):
    """Create a SelectionTemplateManager instance for testing."""
    return SelectionTemplateManager(storage_dir=temp_storage_dir)


@pytest.fixture
def sample_template():
    """Create a sample selection template for testing."""
    config = SelectionConfig(
        include_paths=[Path("/home/user/documents")],
        exclude_paths=[Path("/home/user/documents/temp")],
        include_patterns=[
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB)
        ],
        exclude_patterns=[
            PatternRule(pattern="*.tmp", syntax=PatternSyntax.GLOB)
        ],
        pattern_groups=["office_documents"],
        precedence_config=PrecedenceConfig(),
        case_sensitive=False
    )
    
    return SelectionTemplate(
        id=str(uuid.uuid4()),
        name="Test Template",
        description="A test selection template",
        selection_config=config,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        tags=["test", "documents"],
        usage_count=0,
        is_system_template=False
    )


class TestSelectionTemplateManager:
    """Test suite for SelectionTemplateManager class."""
    
    @pytest.mark.unit
    def test_initialization(self, template_manager, temp_storage_dir):
        """Test SelectionTemplateManager initialization."""
        assert template_manager is not None
        assert template_manager.storage_dir == temp_storage_dir
        assert temp_storage_dir.exists()
        assert len(template_manager.templates_cache) == 0
    
    @pytest.mark.unit
    def test_create_template(self, template_manager, sample_template):
        """Test creating a new template."""
        template_id = template_manager.create_template(sample_template)
        
        assert template_id == sample_template.id
        assert template_id in template_manager.templates_cache
        
        # Verify template file was created
        template_file = template_manager.storage_dir / f"{template_id}.json"
        assert template_file.exists()
    
    @pytest.mark.unit
    def test_create_duplicate_template(self, template_manager, sample_template):
        """Test creating a template with duplicate ID raises error."""
        template_manager.create_template(sample_template)
        
        with pytest.raises(TemplateAlreadyExistsError):
            template_manager.create_template(sample_template)
    
    @pytest.mark.unit
    def test_create_invalid_template(self, template_manager):
        """Test creating an invalid template raises error."""
        # Template without name - will fail at model validation
        with pytest.raises(ValueError):
            invalid_template = SelectionTemplate(
                id=str(uuid.uuid4()),
                name="",
                description="Invalid",
                selection_config=SelectionConfig(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
    
    @pytest.mark.unit
    def test_get_template(self, template_manager, sample_template):
        """Test retrieving a template by ID."""
        initial_usage = sample_template.usage_count
        template_manager.create_template(sample_template)
        
        retrieved = template_manager.get_template(sample_template.id)
        
        assert retrieved.id == sample_template.id
        assert retrieved.name == sample_template.name
        assert retrieved.usage_count > initial_usage  # Should increment
    
    @pytest.mark.unit
    def test_get_nonexistent_template(self, template_manager):
        """Test retrieving a non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_manager.get_template("nonexistent-id")
    
    @pytest.mark.unit
    def test_list_templates(self, template_manager, sample_template):
        """Test listing all templates."""
        template_manager.create_template(sample_template)
        
        # Create another template
        template2 = SelectionTemplate(
            id=str(uuid.uuid4()),
            name="Another Template",
            description="Another test template",
            selection_config=SelectionConfig(
                include_paths=[Path("/home/user")]
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=["test"],
            is_system_template=False
        )
        template_manager.create_template(template2)
        
        templates = template_manager.list_templates()
        
        assert len(templates) == 2
        assert any(t.id == sample_template.id for t in templates)
        assert any(t.id == template2.id for t in templates)
    
    @pytest.mark.unit
    def test_list_templates_with_filters(self, template_manager, sample_template):
        """Test listing templates with filters."""
        template_manager.create_template(sample_template)
        
        # Filter by tag
        templates = template_manager.list_templates(filters={'tags': ['documents']})
        assert len(templates) == 1
        assert templates[0].id == sample_template.id
        
        # Filter by name
        templates = template_manager.list_templates(filters={'name_contains': 'Test'})
        assert len(templates) == 1
        
        # Filter by system template
        templates = template_manager.list_templates(filters={'is_system_template': False})
        assert len(templates) == 1
    
    @pytest.mark.unit
    def test_update_template(self, template_manager, sample_template):
        """Test updating a template."""
        template_manager.create_template(sample_template)
        
        updates = {
            'name': 'Updated Template',
            'description': 'Updated description',
            'tags': ['updated', 'test']
        }
        
        updated = template_manager.update_template(sample_template.id, updates)
        
        assert updated.name == 'Updated Template'
        assert updated.description == 'Updated description'
        assert 'updated' in updated.tags
    
    @pytest.mark.unit
    def test_update_nonexistent_template(self, template_manager):
        """Test updating a non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_manager.update_template("nonexistent-id", {'name': 'New Name'})
    
    @pytest.mark.unit
    def test_update_system_template(self, template_manager):
        """Test updating a system template raises error."""
        system_template = SelectionTemplate(
            id=str(uuid.uuid4()),
            name="System Template",
            description="A system template",
            selection_config=SelectionConfig(
                include_paths=[Path("/home")]
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_system_template=True
        )
        
        template_manager.create_template(system_template)
        
        with pytest.raises(TemplateValidationError):
            template_manager.update_template(system_template.id, {'name': 'New Name'})
    
    @pytest.mark.unit
    def test_delete_template(self, template_manager, sample_template):
        """Test deleting a template."""
        template_manager.create_template(sample_template)
        
        result = template_manager.delete_template(sample_template.id)
        
        assert result is True
        assert sample_template.id not in template_manager.templates_cache
        
        # Verify file was deleted
        template_file = template_manager.storage_dir / f"{sample_template.id}.json"
        assert not template_file.exists()
    
    @pytest.mark.unit
    def test_delete_nonexistent_template(self, template_manager):
        """Test deleting a non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_manager.delete_template("nonexistent-id")
    
    @pytest.mark.unit
    def test_delete_system_template(self, template_manager):
        """Test deleting a system template raises error."""
        system_template = SelectionTemplate(
            id=str(uuid.uuid4()),
            name="System Template",
            description="A system template",
            selection_config=SelectionConfig(
                include_paths=[Path("/home")]
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_system_template=True
        )
        
        template_manager.create_template(system_template)
        
        with pytest.raises(TemplateValidationError):
            template_manager.delete_template(system_template.id)
    
    @pytest.mark.unit
    def test_duplicate_template(self, template_manager, sample_template):
        """Test duplicating a template."""
        template_manager.create_template(sample_template)
        
        new_name = "Duplicated Template"
        duplicated = template_manager.duplicate_template(sample_template.id, new_name)
        
        assert duplicated.id != sample_template.id
        assert duplicated.name == new_name
        assert duplicated.usage_count == 0
        assert not duplicated.is_system_template
        assert duplicated.id in template_manager.templates_cache
    
    @pytest.mark.unit
    def test_duplicate_nonexistent_template(self, template_manager):
        """Test duplicating a non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_manager.duplicate_template("nonexistent-id", "New Name")
    
    @pytest.mark.unit
    def test_get_template_usage(self, template_manager, sample_template):
        """Test getting template usage information."""
        template_manager.create_template(sample_template)
        template_manager.get_template(sample_template.id)  # Increment usage
        
        usage = template_manager.get_template_usage(sample_template.id)
        
        assert usage['template_id'] == sample_template.id
        assert usage['template_name'] == sample_template.name
        assert usage['usage_count'] > 0
        assert 'created_at' in usage
        assert 'updated_at' in usage
    
    @pytest.mark.unit
    def test_export_template_json(self, template_manager, sample_template, temp_storage_dir):
        """Test exporting a template to JSON."""
        template_manager.create_template(sample_template)
        
        output_path = temp_storage_dir / "exported_template.json"
        result_path = template_manager.export_template(
            sample_template.id,
            output_path,
            format='json'
        )
        
        assert result_path == output_path
        assert output_path.exists()
        
        # Verify content
        import json
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert data['id'] == sample_template.id
        assert data['name'] == sample_template.name
    
    @pytest.mark.unit
    def test_export_template_yaml(self, template_manager, sample_template, temp_storage_dir):
        """Test exporting a template to YAML."""
        template_manager.create_template(sample_template)
        
        output_path = temp_storage_dir / "exported_template.yaml"
        result_path = template_manager.export_template(
            sample_template.id,
            output_path,
            format='yaml'
        )
        
        assert result_path == output_path
        assert output_path.exists()
    
    @pytest.mark.unit
    def test_export_nonexistent_template(self, template_manager, temp_storage_dir):
        """Test exporting a non-existent template raises error."""
        output_path = temp_storage_dir / "exported.json"
        
        with pytest.raises(TemplateNotFoundError):
            template_manager.export_template("nonexistent-id", output_path)
    
    @pytest.mark.unit
    def test_export_multiple_templates(self, template_manager, sample_template, temp_storage_dir):
        """Test exporting multiple templates."""
        template_manager.create_template(sample_template)
        
        template2 = SelectionTemplate(
            id=str(uuid.uuid4()),
            name="Template 2",
            description="Second template",
            selection_config=SelectionConfig(
                include_paths=[Path("/home")]
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        template_manager.create_template(template2)
        
        output_path = temp_storage_dir / "exported_templates.json"
        result_path = template_manager.export_templates(
            [sample_template.id, template2.id],
            output_path,
            format='json'
        )
        
        assert result_path == output_path
        assert output_path.exists()
        
        # Verify content
        import json
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert 'templates' in data
        assert len(data['templates']) == 2
    
    @pytest.mark.unit
    def test_import_template(self, template_manager, sample_template, temp_storage_dir):
        """Test importing a template from file."""
        # First export a template
        template_manager.create_template(sample_template)
        export_path = temp_storage_dir / "export.json"
        template_manager.export_template(sample_template.id, export_path)
        
        # Clear cache and import
        template_manager.templates_cache.clear()
        
        result = template_manager.import_template(export_path, merge_strategy='skip')
        
        assert result.success
        assert result.imported_count == 1
        assert sample_template.id in template_manager.templates_cache
    
    @pytest.mark.unit
    def test_import_template_skip_existing(self, template_manager, sample_template, temp_storage_dir):
        """Test importing with skip strategy for existing templates."""
        template_manager.create_template(sample_template)
        
        # Export and try to import again
        export_path = temp_storage_dir / "export.json"
        template_manager.export_template(sample_template.id, export_path)
        
        result = template_manager.import_template(export_path, merge_strategy='skip')
        
        assert result.success
        assert result.skipped_count == 1
        assert result.imported_count == 0
    
    @pytest.mark.unit
    def test_import_template_rename_existing(self, template_manager, sample_template, temp_storage_dir):
        """Test importing with rename strategy for existing templates."""
        template_manager.create_template(sample_template)
        
        # Export and try to import again with rename
        export_path = temp_storage_dir / "export.json"
        template_manager.export_template(sample_template.id, export_path)
        
        result = template_manager.import_template(export_path, merge_strategy='rename')
        
        assert result.success
        assert result.imported_count == 1
        # Should have original and renamed version
        assert len(template_manager.templates_cache) == 2
    
    @pytest.mark.unit
    def test_import_template_overwrite_existing(self, template_manager, sample_template, temp_storage_dir):
        """Test importing with overwrite strategy for existing templates."""
        template_manager.create_template(sample_template)
        
        # Modify and export
        template_manager.update_template(sample_template.id, {'description': 'Modified'})
        export_path = temp_storage_dir / "export.json"
        template_manager.export_template(sample_template.id, export_path)
        
        # Modify again locally
        template_manager.update_template(sample_template.id, {'description': 'Local change'})
        
        # Import with overwrite
        result = template_manager.import_template(export_path, merge_strategy='overwrite')
        
        assert result.success
        assert result.imported_count == 1
        
        # Should have overwritten description
        template = template_manager.get_template(sample_template.id)
        assert template.description == 'Modified'
    
    @pytest.mark.unit
    def test_validate_import_file(self, template_manager, sample_template, temp_storage_dir):
        """Test validating an import file without importing."""
        template_manager.create_template(sample_template)
        export_path = temp_storage_dir / "export.json"
        template_manager.export_template(sample_template.id, export_path)
        
        validation = template_manager.validate_import_file(export_path)
        
        assert validation['valid']
        assert validation['template_count'] == 1
        assert len(validation['errors']) == 0
    
    @pytest.mark.unit
    def test_export_all_templates(self, template_manager, sample_template, temp_storage_dir):
        """Test exporting all templates."""
        template_manager.create_template(sample_template)
        
        template2 = SelectionTemplate(
            id=str(uuid.uuid4()),
            name="Template 2",
            description="Second template",
            selection_config=SelectionConfig(
                include_paths=[Path("/home")]
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        template_manager.create_template(template2)
        
        output_path = temp_storage_dir / "all_templates.json"
        result_path = template_manager.export_all_templates(output_path, include_system=False)
        
        assert result_path == output_path
        assert output_path.exists()
        
        # Verify content
        import json
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert len(data['templates']) == 2
    
    @pytest.mark.unit
    def test_template_persistence(self, temp_storage_dir, sample_template):
        """Test that templates persist across manager instances."""
        # Create template with first manager
        manager1 = SelectionTemplateManager(storage_dir=temp_storage_dir)
        manager1.create_template(sample_template)
        
        # Create new manager instance
        manager2 = SelectionTemplateManager(storage_dir=temp_storage_dir)
        
        # Template should be loaded from storage
        assert sample_template.id in manager2.templates_cache
        retrieved = manager2.get_template(sample_template.id)
        assert retrieved.name == sample_template.name
    
    @pytest.mark.unit
    def test_template_validation_no_include_criteria(self, template_manager):
        """Test validation fails when template has no include criteria."""
        invalid_template = SelectionTemplate(
            id=str(uuid.uuid4()),
            name="Invalid Template",
            description="No include criteria",
            selection_config=SelectionConfig(
                exclude_paths=[Path("/tmp")]
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with pytest.raises(TemplateValidationError) as exc_info:
            template_manager.create_template(invalid_template)
        
        assert "at least one include" in str(exc_info.value).lower()
