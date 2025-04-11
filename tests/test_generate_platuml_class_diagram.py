import unittest
from ast import parse
from Utils.generate_platuml_class_diagram import (
    parse_class_definitions,
    collect_class_info,
    add_composition_relationships,
    ClassInfo
)

class TestPlantUMLGenerator(unittest.TestCase):
    def test_parse_simple_class(self):
        code = """
class SimpleClass:
    def __init__(self):
        pass
"""
        classes = parse_class_definitions(code, "test.py")
        self.assertIn("SimpleClass", classes)
        self.assertEqual(len(classes["SimpleClass"].methods), 1)

    def test_parse_class_with_composition(self):
        code = """
class Container:
    def __init__(self):
        self.item: Item = Item()

class Item:
    pass
"""
        classes = parse_class_definitions(code, "test.py")
        self.assertIn("Container", classes)
        self.assertIn("Item", classes)
        self.assertTrue("Item" in classes["Container"].composition_relationships)

    def test_parse_class_with_inheritance(self):
        code = """
class Parent:
    pass

class Child(Parent):
    pass
"""
        classes = parse_class_definitions(code, "test.py")
        self.assertIn("Parent", classes)
        self.assertIn("Child", classes)
        self.assertEqual(classes["Child"].base_classes, ["Parent"])

    def test_parse_class_with_attributes(self):
        code = """
class TestClass:
    name: str
    age: int
"""
        classes = parse_class_definitions(code, "test.py")
        self.assertIn("TestClass", classes)
        attrs = {name: type_ for name, type_ in classes["TestClass"].attributes}
        self.assertEqual(attrs["name"], "str")
        self.assertEqual(attrs["age"], "int")

    def test_collect_class_info_returns_dict(self):
        code = """
class TestClass:
    pass
"""
        tree = parse(code)
        classes = collect_class_info(tree)
        self.assertIsInstance(classes, dict)
        self.assertIn("TestClass", classes)
        self.assertIsInstance(classes["TestClass"], ClassInfo)

    def test_add_composition_relationships(self):
        code = """
class Container:
    item: Item

class Item:
    pass
"""
        tree = parse(code)
        classes = collect_class_info(tree)
        add_composition_relationships(tree, classes)
        self.assertTrue("Item" in classes["Container"].composition_relationships)

if __name__ == '__main__':
    unittest.main()