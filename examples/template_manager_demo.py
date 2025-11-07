#!/usr/bin/env python3
"""
Demo script for SelectionTemplateManager functionality.

This script demonstrates:
1. Creating selection templates
2. Listing and filtering templates
3. Updating templates
4. Exporting templates to JSON/YAML
5. Importing templates with different merge strategies
6. Duplicating templates
"""

import asyncio
import uuid
from pathlib import Path
from datetime import datetime

from TimeLocker.selection_template_manager import SelectionTemplateManager
from TimeLocker.selection_models import (
    SelectionTemplate,
    SelectionConfig,
    PatternRule,
    PrecedenceConfig,
    PatternSyntax,
    PathComponent,
    PrecedenceStrategy
)


async def demo_template_creation():
    """Demonstrate creating selection templates"""
    print("=" * 60)
    print("Demo 1: Creating Selection Templates")
    print("=" * 60)
    
    # Initialize template manager with a demo directory
    demo_dir = Path("/tmp/timelocker_template_demo")
    manager = SelectionTemplateManager(storage_dir=demo_dir)
    
    # Create a template for Python projects
    python_config = SelectionConfig(
        include_patterns=[
            PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.pyi", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="requirements*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="pyproject.toml", syntax=PatternSyntax.LITERAL),
        ],
        exclude_patterns=[
            PatternRule(pattern="__pycache__", syntax=PatternSyntax.LITERAL),
            PatternRule(pattern="*.pyc", syntax=PatternSyntax.GLOB),
            PatternRule(pattern=".venv", syntax=PatternSyntax.LITERAL),
            PatternRule(pattern="venv", syntax=PatternSyntax.LITERAL),
        ],
        precedence_config=PrecedenceConfig(
            default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE
        )
    )
    
    python_template = SelectionTemplate(
        id=str(uuid.uuid4()),
        name="Python Project",
        description="Standard Python project files excluding virtual environments",
        selection_config=python_config,
        tags=["python", "development", "source-code"],
        created_by="demo_user"
    )
    
    template_id = await manager.create_template(python_template)
    print(f"✓ Created Python template: {template_id}")
    
    # Create a template for documentation
    docs_config = SelectionConfig(
        include_patterns=[
            PatternRule(pattern="*.md", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.rst", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="docs/**", syntax=PatternSyntax.GLOB),
        ],
        exclude_patterns=[
            PatternRule(pattern="node_modules/**", syntax=PatternSyntax.GLOB),
        ]
    )
    
    docs_template = SelectionTemplate(
        id=str(uuid.uuid4()),
        name="Documentation Files",
        description="All documentation and text files",
        selection_config=docs_config,
        tags=["documentation", "text"],
        created_by="demo_user"
    )
    
    docs_id = await manager.create_template(docs_template)
    print(f"✓ Created Documentation template: {docs_id}")
    
    return manager, template_id, docs_id


async def demo_template_listing(manager):
    """Demonstrate listing and filtering templates"""
    print("\n" + "=" * 60)
    print("Demo 2: Listing and Filtering Templates")
    print("=" * 60)
    
    # List all templates
    all_templates = await manager.list_templates()
    print(f"\nTotal templates: {len(all_templates)}")
    for template in all_templates:
        print(f"  - {template.name} ({template.id[:8]}...)")
        print(f"    Tags: {', '.join(template.tags)}")
        print(f"    Usage: {template.usage_count} times")
    
    # Filter by tags
    python_templates = await manager.list_templates(filters={'tags': ['python']})
    print(f"\nPython templates: {len(python_templates)}")
    for template in python_templates:
        print(f"  - {template.name}")
    
    # Filter by name
    doc_templates = await manager.list_templates(
        filters={'name_contains': 'doc'}
    )
    print(f"\nTemplates with 'doc' in name: {len(doc_templates)}")
    for template in doc_templates:
        print(f"  - {template.name}")


async def demo_template_update(manager, template_id):
    """Demonstrate updating templates"""
    print("\n" + "=" * 60)
    print("Demo 3: Updating Templates")
    print("=" * 60)
    
    # Get the template
    template = await manager.get_template(template_id)
    print(f"\nOriginal template: {template.name}")
    print(f"  Description: {template.description}")
    print(f"  Tags: {template.tags}")
    
    # Update the template
    updates = {
        'description': 'Updated: Python project with enhanced exclusions',
        'tags': ['python', 'development', 'source-code', 'updated']
    }
    
    updated_template = await manager.update_template(template_id, updates)
    print(f"\n✓ Updated template")
    print(f"  New description: {updated_template.description}")
    print(f"  New tags: {updated_template.tags}")


async def demo_template_export(manager, template_id):
    """Demonstrate exporting templates"""
    print("\n" + "=" * 60)
    print("Demo 4: Exporting Templates")
    print("=" * 60)
    
    export_dir = Path("/tmp/timelocker_exports")
    export_dir.mkdir(exist_ok=True)
    
    # Export single template as JSON
    json_path = export_dir / "python_template.json"
    await manager.export_template(template_id, json_path, format='json')
    print(f"✓ Exported template to JSON: {json_path}")
    
    # Export single template as YAML
    yaml_path = export_dir / "python_template.yaml"
    await manager.export_template(template_id, yaml_path, format='yaml')
    print(f"✓ Exported template to YAML: {yaml_path}")
    
    # Export all templates
    all_templates_path = export_dir / "all_templates.json"
    await manager.export_all_templates(all_templates_path, format='json')
    print(f"✓ Exported all templates to: {all_templates_path}")
    
    return json_path, yaml_path


async def demo_template_import(manager, export_path):
    """Demonstrate importing templates"""
    print("\n" + "=" * 60)
    print("Demo 5: Importing Templates")
    print("=" * 60)
    
    # Validate import file first
    validation = await manager.validate_import_file(export_path)
    print(f"\nValidation results for {export_path.name}:")
    print(f"  Valid: {validation['valid']}")
    print(f"  Template count: {validation['template_count']}")
    if validation['errors']:
        print(f"  Errors: {validation['errors']}")
    if validation['warnings']:
        print(f"  Warnings: {validation['warnings']}")
    
    # Import with 'skip' strategy (won't overwrite existing)
    result = await manager.import_template(export_path, merge_strategy='skip')
    print(f"\n✓ Import with 'skip' strategy:")
    print(f"  Imported: {result.imported_count}")
    print(f"  Skipped: {result.skipped_count}")
    print(f"  Failed: {result.failed_count}")
    
    # Import with 'rename' strategy (creates new template)
    result = await manager.import_template(export_path, merge_strategy='rename')
    print(f"\n✓ Import with 'rename' strategy:")
    print(f"  Imported: {result.imported_count}")
    print(f"  Skipped: {result.skipped_count}")
    if result.warnings:
        print(f"  Warnings: {result.warnings[0]}")


async def demo_template_duplication(manager, template_id):
    """Demonstrate duplicating templates"""
    print("\n" + "=" * 60)
    print("Demo 6: Duplicating Templates")
    print("=" * 60)
    
    # Get original template
    original = await manager.get_template(template_id)
    print(f"\nOriginal template: {original.name}")
    
    # Duplicate it
    duplicate = await manager.duplicate_template(template_id, "Python Project (Copy)")
    print(f"✓ Created duplicate: {duplicate.name}")
    print(f"  New ID: {duplicate.id}")
    print(f"  Same config: {duplicate.selection_config == original.selection_config}")


async def demo_template_usage(manager, template_id):
    """Demonstrate template usage tracking"""
    print("\n" + "=" * 60)
    print("Demo 7: Template Usage Tracking")
    print("=" * 60)
    
    # Get template multiple times to increment usage
    for i in range(3):
        await manager.get_template(template_id)
    
    # Check usage
    usage = await manager.get_template_usage(template_id)
    print(f"\nTemplate usage information:")
    print(f"  Name: {usage['template_name']}")
    print(f"  Usage count: {usage['usage_count']}")
    print(f"  Created: {usage['created_at']}")
    print(f"  Last used: {usage['last_used']}")


async def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("SelectionTemplateManager Demo")
    print("=" * 60)
    
    # Demo 1: Create templates
    manager, python_id, docs_id = await demo_template_creation()
    
    # Demo 2: List and filter
    await demo_template_listing(manager)
    
    # Demo 3: Update template
    await demo_template_update(manager, python_id)
    
    # Demo 4: Export templates
    json_path, yaml_path = await demo_template_export(manager, python_id)
    
    # Demo 5: Import templates
    await demo_template_import(manager, json_path)
    
    # Demo 6: Duplicate template
    await demo_template_duplication(manager, python_id)
    
    # Demo 7: Usage tracking
    await demo_template_usage(manager, python_id)
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)
    print(f"\nTemplate storage: {manager.storage_dir}")
    print(f"Export directory: /tmp/timelocker_exports")


if __name__ == "__main__":
    asyncio.run(main())
