"""Tests for PlantUML generator functionality."""

import unittest
from Utils.puml_generator.config import PlantUMLConfig
from Utils.puml_generator.plantuml_generator import generate_plantuml_content
from Utils.puml_generator.class_info import ClassInfo

class TestPlantUMLGenerator(unittest.TestCase):
    """Test cases for PlantUML generator."""

    def test_skin_and_theme_settings(self):
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
        self.assertIn("skin plantuml", content)
        self.assertIn("!theme _none_", content)

        # Test with default settings
        config = PlantUMLConfig()  # Uses default skin and theme
        content = generate_plantuml_content(test_classes, "test_package", config)
        self.assertIn("skin plantuml", content)
        self.assertIn("!theme _none_", content)

        # Test with custom skin only
        config = PlantUMLConfig(skin="debug", theme=None)
        content = generate_plantuml_content(test_classes, "test_package", config)
        self.assertIn("skin debug", content)
        self.assertNotIn("!theme", content)

        # Test with skin and different theme
        config = PlantUMLConfig(skin="rose", theme="amiga")
        content = generate_plantuml_content(test_classes, "test_package", config)
        self.assertIn("skin rose", content)
        self.assertIn("!theme amiga", content)

if __name__ == '__main__':
    unittest.main()
