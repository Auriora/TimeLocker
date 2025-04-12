from ast import parse
from Utils.puml_generator import (
    parse_class_definitions,
    ClassInfo,
    PlantUMLConfig,
    ProjectConfig,
    ElementType
)
from Utils.puml_generator.class_parser import collect_class_info, add_composition_relationships


def test_parse_simple_class():
    code = """
class SimpleClass:
    def __init__(self):
        pass
"""
    classes = parse_class_definitions(code, "src/test.py")
    assert "SimpleClass" in classes
    assert len(classes["SimpleClass"].methods) == 1
    assert classes["SimpleClass"].full_name == "src.test.SimpleClass"


def test_parse_class_with_composition():
    code = """
class Container:
    def __init__(self):
        self.item: Item = Item()

class Item:
    pass
"""
    classes = parse_class_definitions(code, "src/models/test.py")
    assert "Container" in classes
    assert "Item" in classes
    assert "Item" in classes["Container"].composition_relationships
    assert classes["Container"].full_name == "src.models.test.Container"
    assert classes["Item"].full_name == "src.models.test.Item"


def test_parse_class_with_inheritance():
    code = """
class Parent:
    pass

class Child(Parent):
    pass
"""
    classes = parse_class_definitions(code, "src/test.py")
    assert "Parent" in classes
    assert "Child" in classes
    assert classes["Child"].base_classes == ["Parent"]
    assert classes["Parent"].full_name == "src.test.Parent"
    assert classes["Child"].full_name == "src.test.Child"


def test_parse_class_with_attributes():
    code = """
class TestClass:
    name: str
    _protected: int
    __private: bool
"""
    classes = parse_class_definitions(code, "src/models/test.py")
    assert "TestClass" in classes
    attrs = {name: (type_, vis) for name, type_, vis, _ in classes["TestClass"].attributes}
    assert attrs["name"] == ("str", "+")
    assert attrs["_protected"] == ("int", "#")
    assert attrs["__private"] == ("bool", "-")


def test_parse_class_with_methods():
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
    assert "TestClass" in classes
    methods = {name: (params, vis) for name, params, vis, _ in classes["TestClass"].methods}
    assert methods["public_method"] == ("", "+")
    assert methods["_protected_method"] == ("", "#")
    assert methods["__private_method"] == ("", "-")
    assert classes["TestClass"].full_name == "src.models.test.TestClass"


def test_collect_class_info_returns_dict():
    code = """
class TestClass:
    pass
"""
    tree = parse(code)
    classes = collect_class_info(tree, "src.test")
    assert isinstance(classes, dict)
    assert "TestClass" in classes
    assert isinstance(classes["TestClass"], ClassInfo)
    assert classes["TestClass"].full_name == "src.test.TestClass"


def test_add_composition_relationships():
    code = """
class Container:
    item: Item

class Item:
    pass
"""
    tree = parse(code)
    classes = collect_class_info(tree, "src.models")
    add_composition_relationships(tree, classes)
    assert "Item" in classes["Container"].composition_relationships
    assert classes["Container"].full_name == "src.models.Container"
    assert classes["Item"].full_name == "src.models.Item"


def test_class_info_full_name():
    # Test without module path
    class_info = ClassInfo("TestClass")
    assert class_info.full_name == "TestClass"

    # Test with module path
    class_info = ClassInfo("TestClass", "src.models")
    assert class_info.full_name == "src.models.TestClass"


def test_plantuml_config_defaults():
    config = PlantUMLConfig()
    assert config.server_url == 'http://www.plantuml.com/plantuml/svg/'
    assert config.output_format == 'svg'
    assert config.basic_auth == {}
    assert config.form_auth == {}
    assert config.http_opts == {}
    assert config.request_opts == {}


def test_plantuml_config_none_output():
    config = PlantUMLConfig(output_format=None)
    assert config.server_url == 'http://www.plantuml.com/plantuml/'
    assert config.output_format is None
    assert config.basic_auth == {}
    assert config.form_auth == {}
    assert config.http_opts == {}
    assert config.request_opts == {}


def test_project_config():
    config = ProjectConfig(
        src_dir='src',
        output_dir='docs/diagrams',
        excluded_dirs=['__pycache__', 'tests'],
        package_base_name='myproject'
    )
    assert config.src_dir.endswith('/src')
    assert config.output_dir.endswith('/docs/diagrams')
    assert config.excluded_dirs == ['__pycache__', 'tests']
    assert config.package_base_name == 'myproject'


def test_parse_class_with_package_base_name():
    code = """
class TestClass:
    pass
"""
    # Test without package base name
    classes = parse_class_definitions(code, "src/test.py")
    assert classes["TestClass"].full_name == "src.test.TestClass"

    # Test with package base name
    classes = parse_class_definitions(code, "src/test.py", "myproject")
    assert classes["TestClass"].full_name == "myproject.src.test.TestClass"


def test_exception_detection():
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
    assert "CustomException" in classes
    assert classes["CustomException"].element_type == ElementType.EXCEPTION
    
    # Test class with Error in name
    assert "DatabaseError" in classes
    assert classes["DatabaseError"].element_type == ElementType.EXCEPTION
    
    # Test class with Exception in name
    assert "ValidationException" in classes
    assert classes["ValidationException"].element_type == ElementType.EXCEPTION
    
    # Test inheritance from another exception class
    assert "NetworkError" in classes
    assert classes["NetworkError"].element_type == ElementType.EXCEPTION
    
    # Test normal class
    assert "NormalClass" in classes
    assert classes["NormalClass"].element_type == ElementType.CLASS















