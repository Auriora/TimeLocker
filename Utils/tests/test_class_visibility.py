"""Tests for class member visibility functionality."""

import pytest
from ..puml_generator.class_parser import determine_visibility, parse_class_definitions

def test_determine_visibility():
    """Test visibility determination based on Python naming conventions."""
    # Test private members (double underscore)
    assert determine_visibility("__private_method") == "-"
    assert determine_visibility("__private_attr") == "-"
    
    # Test protected members (single underscore)
    assert determine_visibility("_protected_method") == "#"
    assert determine_visibility("_protected_attr") == "#"
    
    # Test public members (no underscore)
    assert determine_visibility("public_method") == "+"
    assert determine_visibility("public_attr") == "+"

def test_class_member_visibility():
    """Test visibility in parsed class definitions."""
    class_code = '''
class TestClass:
    public_attr = "public"
    _protected_attr = "protected"
    __private_attr = "private"
    
    def public_method(self):
        pass
        
    def _protected_method(self):
        pass
        
    def __private_method(self):
        pass
    '''
    
    classes = parse_class_definitions(class_code, "test.py")
    test_class = classes["TestClass"]
    
    # Check attributes visibility
    attributes = {name: vis for name, _, vis, _ in test_class.attributes}
    assert attributes["public_attr"] == "+"
    assert attributes["_protected_attr"] == "#"
    assert attributes["__private_attr"] == "-"
    
    # Check methods visibility
    methods = {name: vis for name, _, vis, _ in test_class.methods}
    assert methods["public_method"] == "+"
    assert methods["_protected_method"] == "#"
    assert methods["__private_method"] == "-"

def test_visibility_in_plantuml_output():
    """Test that visibility is correctly represented in PlantUML output."""
    class_code = '''
class TestClass:
    public_attr: str = "public"
    _protected_attr: str = "protected"
    __private_attr: str = "private"
    
    def public_method(self):
        pass
        
    def _protected_method(self):
        pass
        
    def __private_method(self):
        pass
    '''
    
    classes = parse_class_definitions(class_code, "test.py")
    test_class = classes["TestClass"]
    plantuml = test_class.to_plantuml()
    
    # Check that visibility modifiers appear correctly in PlantUML
    assert "+ public_attr: str" in plantuml
    assert "# _protected_attr: str" in plantuml
    assert "- __private_attr: str" in plantuml
    assert "+ public_method()" in plantuml
    assert "# _protected_method()" in plantuml
    assert "- __private_method()" in plantuml