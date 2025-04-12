import unittest
from ast import parse
from Utils.puml_generator import (
    parse_class_definitions,
    ClassInfo,
    PlantUMLConfig,
    ProjectConfig,
    ElementType
)
from Utils.puml_generator.class_parser import collect_class_info, add_composition_relationships


class TestPlantUMLGenerator(unittest.TestCase):
    def test_parse_simple_class(self):
        code = """
class SimpleClass:
    def __init__(self):
        pass
"""
        classes = parse_class_definitions(code, "src/test.py")
        self.assertIn("SimpleClass", classes)
        self.assertEqual(len(classes["SimpleClass"].methods), 1)
        self.assertEqual(classes["SimpleClass"].full_name, "src.test.SimpleClass")

    def test_parse_class_with_composition(self):
        code = """
class Container:
    def __init__(self):
        self.item: Item = Item()

class Item:
    pass
"""
        classes = parse_class_definitions(code, "src/models/test.py")
        self.assertIn("Container", classes)
        self.assertIn("Item", classes)
        self.assertTrue("Item" in classes["Container"].composition_relationships)
        self.assertEqual(classes["Container"].full_name, "src.models.test.Container")
        self.assertEqual(classes["Item"].full_name, "src.models.test.Item")

    def test_parse_class_with_inheritance(self):
        code = """
class Parent:
    pass

class Child(Parent):
    pass
"""
        classes = parse_class_definitions(code, "src/test.py")
        self.assertIn("Parent", classes)
        self.assertIn("Child", classes)
        self.assertEqual(classes["Child"].base_classes, ["Parent"])
        self.assertEqual(classes["Parent"].full_name, "src.test.Parent")
        self.assertEqual(classes["Child"].full_name, "src.test.Child")

    def test_parse_class_with_attributes(self):
        code = """
class TestClass:
    name: str
    _protected: int
    __private: bool
"""
        classes = parse_class_definitions(code, "src/models/test.py")
        self.assertIn("TestClass", classes)
        attrs = {name: (type_, vis) for name, type_, vis, _ in classes["TestClass"].attributes}
        self.assertEqual(attrs["name"], ("str", "+"))
        self.assertEqual(attrs["_protected"], ("int", "#"))
        self.assertEqual(attrs["__private"], ("bool", "-"))
    def test_parse_class_with_methods(self):
        code = """
class TestClass:
    def public_method(self):
        pass
        
    def _protected_method(self):
        pass
        
    def __private_method(self):
        pass
"""
        classes = parse_class_definitions(code, "src/models/test.py")
        self.assertIn("TestClass", classes)
        methods = {name: (params, vis) for name, params, vis, _ in classes["TestClass"].methods}
        self.assertEqual(methods["public_method"], ("", "+"))
        self.assertEqual(methods["_protected_method"], ("", "#"))
        self.assertEqual(methods["__private_method"], ("", "-"))
        self.assertEqual(classes["TestClass"].full_name, "src.models.test.TestClass")

    def test_collect_class_info_returns_dict(self):
        code = """
class TestClass:
    pass
"""
        tree = parse(code)
        classes = collect_class_info(tree, "src.test")
        self.assertIsInstance(classes, dict)
        self.assertIn("TestClass", classes)
        self.assertIsInstance(classes["TestClass"], ClassInfo)
        self.assertEqual(classes["TestClass"].full_name, "src.test.TestClass")

    def test_add_composition_relationships(self):
        code = """
class Container:
    item: Item

class Item:
    pass
"""
        tree = parse(code)
        classes = collect_class_info(tree, "src.models")
        add_composition_relationships(tree, classes)
        self.assertTrue("Item" in classes["Container"].composition_relationships)
        self.assertEqual(classes["Container"].full_name, "src.models.Container")
        self.assertEqual(classes["Item"].full_name, "src.models.Item")

    def test_class_info_full_name(self):
        # Test without module path
        class_info = ClassInfo("TestClass")
        self.assertEqual(class_info.full_name, "TestClass")

        # Test with module path
        class_info = ClassInfo("TestClass", "src.models")
        self.assertEqual(class_info.full_name, "src.models.TestClass")

    def test_plantuml_config_defaults(self):
        config = PlantUMLConfig()
        self.assertEqual(config.server_url, 'http://www.plantuml.com/plantuml/svg/')
        self.assertEqual(config.output_format, 'svg')
        self.assertEqual(config.basic_auth, {})
        self.assertEqual(config.form_auth, {})
        self.assertEqual(config.http_opts, {})
        self.assertEqual(config.request_opts, {})

    def test_plantuml_config_none_output(self):
        config = PlantUMLConfig(output_format=None)
        self.assertEqual(config.server_url, 'http://www.plantuml.com/plantuml/')
        self.assertIsNone(config.output_format)
        self.assertEqual(config.basic_auth, {})
        self.assertEqual(config.form_auth, {})
        self.assertEqual(config.http_opts, {})
        self.assertEqual(config.request_opts, {})

    def test_project_config(self):
        config = ProjectConfig(
            src_dir='src',
            output_dir='docs/diagrams',
            excluded_dirs=['__pycache__', 'tests'],
            package_base_name='myproject'
        )
        self.assertTrue(config.src_dir.endswith('/src'))
        self.assertTrue(config.output_dir.endswith('/docs/diagrams'))
        self.assertEqual(config.excluded_dirs, ['__pycache__', 'tests'])
        self.assertEqual(config.package_base_name, 'myproject')

    def test_parse_class_with_package_base_name(self):
        code = """
class TestClass:
    pass
"""
        # Test without package base name
        classes = parse_class_definitions(code, "src/test.py")
        self.assertEqual(classes["TestClass"].full_name, "src.test.TestClass")

        # Test with package base name
        classes = parse_class_definitions(code, "src/test.py", "myproject")
        self.assertEqual(classes["TestClass"].full_name, "myproject.src.test.TestClass")

    def test_exception_detection(self):
        code = """
class CustomException(Exception):
    pass

class DatabaseError:
    pass

class ValidationException:
    pass

class NetworkError(CustomException):
    pass

class NormalClass:
    pass
"""
        classes = parse_class_definitions(code, "src/test.py")
        
        # Test direct inheritance from Exception
        self.assertIn("CustomException", classes)
        self.assertEqual(classes["CustomException"].element_type, ElementType.EXCEPTION)
        
        # Test class with Error in name
        self.assertIn("DatabaseError", classes)
        self.assertEqual(classes["DatabaseError"].element_type, ElementType.EXCEPTION)
        
        # Test class with Exception in name
        self.assertIn("ValidationException", classes)
        self.assertEqual(classes["ValidationException"].element_type, ElementType.EXCEPTION)
        
        # Test inheritance from another exception class
        self.assertIn("NetworkError", classes)
        self.assertEqual(classes["NetworkError"].element_type, ElementType.EXCEPTION)
        
        # Test normal class
        self.assertIn("NormalClass", classes)
        self.assertEqual(classes["NormalClass"].element_type, ElementType.CLASS)

if __name__ == '__main__':
    unittest.main()














