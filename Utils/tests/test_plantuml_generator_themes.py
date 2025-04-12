"""Tests for PlantUML generator functionality."""

from Utils.puml_generator.config import PlantUMLConfig
from Utils.puml_generator.plantuml_generator import generate_plantuml_content
from Utils.puml_generator.class_info import ClassInfo


def test_skin_and_theme_settings():
    """Test that skin and theme settings are correctly included in PlantUML content."""
    # Create a minimal test setup
    test_classes = {
        "TestClass": ClassInfo("TestClass", "test_module.py")
    }

    # Test with both skin and theme
    config = PlantUMLConfig(
        skin="plantuml",
        theme="_none_"
    )
    content = generate_plantuml_content(test_classes, "test_package", config)
    assert "skin plantuml" in content
    assert "!theme _none_" in content

    # Test with default settings
    config = PlantUMLConfig()  # Uses default skin and theme
    content = generate_plantuml_content(test_classes, "test_package", config)
    assert "skin plantuml" in content
    assert "!theme _none_" in content

    # Test with custom skin only
    config = PlantUMLConfig(skin="debug", theme=None)
    content = generate_plantuml_content(test_classes, "test_package", config)
    assert "skin debug" in content
    assert "!theme" not in content

    # Test with skin and different theme
    config = PlantUMLConfig(skin="rose", theme="amiga")
    content = generate_plantuml_content(test_classes, "test_package", config)
    assert "skin rose" in content
    assert "!theme amiga" in content

