"""
Tests for scheduling integration clients.
"""

from pathlib import Path

import pytest

from src.TimeLocker.scheduling.integration_clients import DataSelectionClient
from src.TimeLocker.selection_template_manager import SelectionTemplateManager
from src.TimeLocker.selection_models import SelectionTemplate, SelectionConfig
from src.TimeLocker.selection_manager import SelectionManager


@pytest.fixture
def sample_selection_manager(tmp_path):
    """Provide a SelectionManager with a single template for testing."""
    storage_dir = tmp_path / "scheduling-templates"
    template_manager = SelectionTemplateManager(storage_dir=storage_dir)
    template = SelectionTemplate(
        id="selection-docs",
        name="Documents",
        description="Documents template",
        selection_config=SelectionConfig(
            include_paths=[Path("/data/documents")]
        )
    )
    template_manager.create_template(template)

    manager = SelectionManager(template_manager=template_manager)
    return manager, template


def test_get_selection_template_resolves_name(sample_selection_manager):
    """DataSelectionClient should resolve friendly names to template IDs."""
    manager, template = sample_selection_manager
    client = DataSelectionClient(selection_manager=manager)

    resolved = client.get_selection_template("Documents")

    assert resolved is not None
    assert resolved.id == template.id


def test_get_selection_template_missing_returns_none(sample_selection_manager):
    """Unknown selections should return None instead of raising."""
    manager, _ = sample_selection_manager
    client = DataSelectionClient(selection_manager=manager)

    assert client.get_selection_template("missing-template") is None
