import textwrap
from Utils.puml_generator import (
    parse_class_definitions,
    ClassInfo,
)


def test_relationships():
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
    assert "Whole" in classes, "Whole class should be parsed."
    assert "ComposedPart" in classes, "ComposedPart class should be parsed."
    assert "ComposedPart" in classes["Whole"].composition_relationships, \
        "Whole should have a composition relationship with ComposedPart."


def test_class_info_to_plantuml_with_modifiers():
    """
    Test conversion of a ClassInfo instance with static and abstract modifiers to PlantUML syntax.
    """
    class_info = ClassInfo("TestClass", "src.test")
    # Test both static and abstract modifiers in different positions
    class_info.attributes = [
        ("static_field", "str", "+", ["static"]),  # Static at start
        ("classifier_field", "int", "-", ["classifier"]),  # Classifier instead of static
        ("abstract_field", "float", "#", ["abstract"])  # Abstract at start
    ]
    class_info.methods = [
        ("static_method", "str -> None", "+", ["static"]),  # Static at start
        ("abstract_method", "self", "#", ["abstract"]),  # Abstract at start
        ("classifier_method", "self, x: int", "-", ["classifier"])  # Classifier instead of static
    ]

    expected_puml = textwrap.dedent("""\
        class src.test.TestClass {
            - {classifier} classifier_field: int
            # {abstract} abstract_field: float
            + {static} static_field: str
            - {classifier} classifier_method(self, x: int)
            # {abstract} abstract_method(self)
            + {static} static_method(str -> None)
        }""")

    actual_puml = class_info.to_plantuml().strip()
    assert actual_puml == expected_puml.strip(), \
        "PlantUML output should include static and abstract modifiers in the correct format."


def test_class_info_to_plantuml_without_modifiers():
    """
    Test that regular members without modifiers are formatted correctly.
    """
    class_info = ClassInfo("TestClass", "src.test")
    class_info.attributes = [("name", "str", "-", []), ("age", "int", "-", [])]
    class_info.methods = [("__init__", "self", "+", []), ("get_name", "self -> str", "+", [])]

    expected_puml = textwrap.dedent("""\
        class src.test.TestClass {
            - name: str
            - age: int
            + __init__(self)
            + get_name(self -> str)
        }""")

    actual_puml = class_info.to_plantuml().strip()
    assert actual_puml == expected_puml.strip(), \
        "PlantUML output should match the expected format."

