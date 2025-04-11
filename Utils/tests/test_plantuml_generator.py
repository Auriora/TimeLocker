import unittest
import textwrap
from Utils.puml_generator import (
    parse_class_definitions,
    ClassInfo,
)


class TestPlantUMLGenerator(unittest.TestCase):
    def test_relationships(self):
        """
        Test that parse_class_definitions correctly identifies
        a composition relationship between Whole and ComposedPart.
        """
        code = textwrap.dedent("""
            class Whole:
                def __init__(self):
                    self.part: ComposedPart = ComposedPart()

            class ComposedPart:
                pass
        """)
        classes = parse_class_definitions(code, "src/test.py")
        self.assertIn("Whole", classes, "Whole class should be parsed.")
        self.assertIn("ComposedPart", classes, "ComposedPart class should be parsed.")
        self.assertIn("ComposedPart", classes["Whole"].composition_relationships,
                      "Whole should have a composition relationship with ComposedPart.")

        def test_class_info_to_plantuml(self):
            """
            Test conversion of a ClassInfo instance to the expected PlantUML syntax.
            """
            class_info = ClassInfo("TestClass", "src.test")
            class_info.attributes = [("name", "str"), ("age", "int")]
            class_info.methods = [("__init__", "self"), ("get_name", "self -> str")]

            expected_puml = textwrap.dedent("""\
                class src.test.TestClass {
                    - name: str
                    - age: int
                    + __init__(self)
                    + get_name(self -> str)
                }""")

            actual_puml = class_info.to_plantuml().strip()
            self.assertEqual(actual_puml, expected_puml.strip(),
                             "PlantUML output should match the expected format.")

    if __name__ == '__main__':
        unittest.main()
