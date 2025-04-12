"""Tests for method modifier detection in class parser."""

import unittest
from textwrap import dedent
from Utils.puml_generator.class_parser import parse_class_definitions

class TestMethodModifiers(unittest.TestCase):
    """Test cases for method modifier detection."""

    def test_static_method_detection(self):
        """Test that static methods are correctly identified."""
        code = dedent('''
            class TestClass:
                @staticmethod
                def static_method():
                    pass
                
                def regular_method(self):
                    pass
        ''')
        
        classes = parse_class_definitions(code, "test.py")
        test_class = classes["TestClass"]
        
        # Find the static method
        static_method = next((m for m in test_class.methods if m[0] == "static_method"), None)
        self.assertIsNotNone(static_method)
        self.assertIn("static", static_method[3])  # Check modifiers list
        
        # Find the regular method
        regular_method = next((m for m in test_class.methods if m[0] == "regular_method"), None)
        self.assertIsNotNone(regular_method)
        self.assertNotIn("static", regular_method[3])  # Check modifiers list

    def test_abstract_method_detection(self):
        """Test that abstract methods are correctly identified."""
        code = dedent('''
            from abc import ABC, abstractmethod
            
            class AbstractClass(ABC):
                @abstractmethod
                def abstract_method(self):
                    pass
                
                def regular_method(self):
                    pass
        ''')
        
        classes = parse_class_definitions(code, "test.py")
        abstract_class = classes["AbstractClass"]
        
        # Find the abstract method
        abstract_method = next((m for m in abstract_class.methods if m[0] == "abstract_method"), None)
        self.assertIsNotNone(abstract_method)
        self.assertIn("abstract", abstract_method[3])  # Check modifiers list
        
        # Find the regular method
        regular_method = next((m for m in abstract_class.methods if m[0] == "regular_method"), None)
        self.assertIsNotNone(regular_method)
        self.assertNotIn("abstract", regular_method[3])  # Check modifiers list

    def test_classmethod_detection(self):
        """Test that class methods are correctly identified."""
        code = dedent('''
            class TestClass:
                @classmethod
                def class_method(cls):
                    pass
                
                def regular_method(self):
                    pass
        ''')
        
        classes = parse_class_definitions(code, "test.py")
        test_class = classes["TestClass"]
        
        # Find the class method
        class_method = next((m for m in test_class.methods if m[0] == "class_method"), None)
        self.assertIsNotNone(class_method)
        self.assertIn("classifier", class_method[3])  # Check modifiers list
        
        # Find the regular method
        regular_method = next((m for m in test_class.methods if m[0] == "regular_method"), None)
        self.assertIsNotNone(regular_method)
        self.assertNotIn("classifier", regular_method[3])  # Check modifiers list

    def test_static_field_detection(self):
        """Test that static fields are correctly identified."""
        code = dedent('''
            class TestClass:
                static_field: str = "test"
                
                def __init__(self):
                    self.instance_field = "test"
        ''')
        
        classes = parse_class_definitions(code, "test.py")
        test_class = classes["TestClass"]
        
        # Find the static field
        static_field = next((a for a in test_class.attributes if a[0] == "static_field"), None)
        self.assertIsNotNone(static_field)
        self.assertIn("static", static_field[3])  # Check modifiers list
        
        # Find the instance field
        instance_field = next((a for a in test_class.attributes if a[0] == "instance_field"), None)
        self.assertIsNotNone(instance_field)
        self.assertNotIn("static", instance_field[3])  # Check modifiers list

if __name__ == '__main__':
    unittest.main()