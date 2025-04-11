import unittest
from ast import parse
from Utils.generate_platuml_class_diagram import (
    ClassInfo, ClassRelationshipVisitor, ElementType, RelationType,
    collect_class_info
)

class TestPlantUMLGenerator(unittest.TestCase):
    def test_element_types(self):
        """Test detection of different element types."""
        code = """
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass

class BaseClass:
    pass

@dataclass
class StructClass:
    field: str

class AbstractClass(ABC):
    @abstractmethod
    def abstract_method(self):
        pass

class Interface(ABC):
    @abstractmethod
    def method1(self): pass
    @abstractmethod
    def method2(self): pass

class EnumClass(Enum):
    VALUE1 = 1
    VALUE2 = 2

class CustomException(Exception):
    pass

class Implementation(Interface):
    def method1(self):
        pass
    def method2(self):
        pass
"""
        tree = parse(code)
        visitor = ClassRelationshipVisitor()
        visitor.visit(tree)

        # Test element type detection
        self.assertEqual(visitor.element_types.get("BaseClass"), ElementType.CLASS)
        self.assertEqual(visitor.element_types.get("StructClass"), ElementType.STRUCT)
        self.assertEqual(visitor.element_types.get("AbstractClass"), ElementType.ABSTRACT_CLASS)
        self.assertEqual(visitor.element_types.get("Interface"), ElementType.INTERFACE)
        self.assertEqual(visitor.element_types.get("EnumClass"), ElementType.ENUM)
        self.assertEqual(visitor.element_types.get("CustomException"), ElementType.EXCEPTION)

    def test_relationships(self):
        """Test detection of different relationship types."""
        code = """
from abc import ABC, abstractmethod
from typing import List

class Interface(ABC):
    @abstractmethod
    def method(self): pass

class Part:
    pass

class Implementation(Interface):
    def method(self):
        pass

class Whole:
    # Strong whole-part relationship
    composed_part: 'ComposedPart'
    # Weak whole-part relationship
    aggregated_part: 'AggregatedPart'
    # Strong dependency
    dependency: 'Dependency'
    # Weak dependency
    weak_dependency: 'WeakDependency'

class ComposedPart:
    pass

class AggregatedPart:
    pass

class Dependency:
    pass

class WeakDependency:
    pass
"""
        tree = parse(code)
        classes = collect_class_info(tree)

        # Test inheritance relationship
        self.assertIn("Interface", classes["Implementation"].base_classes)

        # Test composition relationship
        self.assertIn("ComposedPart", classes["Whole"].composition_relationships)

        # Test aggregation relationship
        self.assertIn("AggregatedPart", classes["Whole"].aggregation_relationships)

        # Test dependency relationships
        self.assertIn("Dependency", classes["Whole"].dependencies)
        self.assertIn("WeakDependency", classes["Whole"].weak_dependencies)

    def test_class_info_to_plantuml(self):
        """Test conversion of class info to PlantUML syntax."""
        class_info = ClassInfo("TestClass")
        class_info.element_type = ElementType.CLASS
        class_info.attributes = [("field1", "str"), ("field2", "int")]
        class_info.methods = [("method1", "param: str"), ("method2", "")]

        expected_puml = """class TestClass {
    - field1: str
    - field2: int
    + method1(param: str)
    + method2()
}"""
        self.assertEqual(class_info.to_plantuml().strip(), expected_puml.strip())

    def test_stereotypes(self):
        """Test handling of stereotypes."""
        code = """
@stereotype("entity")
class Entity:
    pass

@stereotype("controller")
class Controller:
    pass
"""
        tree = parse(code)
        visitor = ClassRelationshipVisitor()
        visitor.visit(tree)

        # Test stereotype detection
        self.assertEqual(visitor.stereotypes.get("Entity"), "entity")
        self.assertEqual(visitor.stereotypes.get("Controller"), "controller")

if __name__ == '__main__':
    unittest.main()