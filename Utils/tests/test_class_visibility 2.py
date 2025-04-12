"""Test class visibility in PlantUML generation."""

from Utils.puml_generator.class_parser import parse_class_definitions

def test_class_visibility():
    """Test that class visibility is correctly detected and represented in PlantUML."""
    code = '''
class PublicClass:
    pass

class _ProtectedClass:
    pass

class __PrivateClass:
    pass

class _abc_PackagePrivateClass:
    pass
'''
    
    classes = parse_class_definitions(code, "test.py")
    
    # Check that all classes were found
    assert "PublicClass" in classes
    assert "_ProtectedClass" in classes
    assert "__PrivateClass" in classes
    assert "_abc_PackagePrivateClass" in classes
    
    # Check visibility modifiers
    assert classes["PublicClass"].visibility == "+"
    assert classes["_ProtectedClass"].visibility == "#"
    assert classes["__PrivateClass"].visibility == "-"
    assert classes["_abc_PackagePrivateClass"].visibility == "~"

def test_class_visibility_in_puml():
    """Test that class visibility is correctly included in PlantUML output."""
    code = '''
class PublicClass:
    pass

class _ProtectedClass:
    pass

class __PrivateClass:
    pass

class _abc_PackagePrivateClass:
    pass
'''
    
    classes = parse_class_definitions(code, "test.py")
    
    # Check PlantUML output
    public_puml = classes["PublicClass"].to_plantuml()
    protected_puml = classes["_ProtectedClass"].to_plantuml()
    private_puml = classes["__PrivateClass"].to_plantuml()
    package_puml = classes["_abc_PackagePrivateClass"].to_plantuml()
    
    # Each class should start with its visibility modifier
    assert public_puml.startswith("+class")
    assert protected_puml.startswith("#class")
    assert private_puml.startswith("-class")
    assert package_puml.startswith("~class")

def test_class_visibility_with_members():
    """Test that class visibility works correctly with class members."""
    code = '''
class _ProtectedClass:
    def __init__(self):
        self._protected_attr = 1
        
    def public_method(self):
        pass
        
    def _protected_method(self):
        pass
'''
    
    classes = parse_class_definitions(code, "test.py")
    puml = classes["_ProtectedClass"].to_plantuml()
    
    # Class should have protected visibility
    assert puml.startswith("#class")
    
    # Members should maintain their own visibility
    lines = puml.split("\n")
    assert any(line.strip().startswith("# _protected_attr") for line in lines)
    assert any(line.strip().startswith("+ public_method") for line in lines)
    assert any(line.strip().startswith("# _protected_method") for line in lines)
