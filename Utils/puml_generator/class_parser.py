"""AST parsing and class information extraction."""

from ast import parse, Name, AST, Subscript, Index, FunctionDef, walk, ClassDef, Attribute
from typing import Dict, List, Optional
from abc import abstractmethod
# from functools import staticmethod

from .class_info import ClassInfo
from .relationship_visitor import ClassRelationshipVisitor

def extract_type_hint(node: AST) -> str:
    """Extract type hint from an AST node."""
    if isinstance(node, Name):
        return node.id
    elif isinstance(node, Subscript):
        base = extract_type_hint(node.value)
        if isinstance(node.slice, Name):
            return f"{base}[{node.slice.id}]"
        elif isinstance(node.slice, Index) and isinstance(node.slice.value, Name):
            return f"{base}[{node.slice.value.id}]"
    return "Any"

def determine_visibility(name: str) -> str:
    """Determine member visibility based on Python naming conventions.
    
    Args:
        name: The name of the method or attribute
        
    Returns:
        The visibility modifier for PlantUML (-, #, ~, or +)
    """
    if name.startswith("__"):
        return "-"  # private
    elif name.startswith("_"):
        return "#"  # protected
    return "+"  # public
def determine_class_visibility(name: str) -> str:
    """Determine class visibility based on Python naming conventions.
    
    Args:
        name: The name of the class
        
    Returns:
        The visibility modifier for PlantUML (-, #, ~, or +)
    """
    if name.startswith("__"):
        return "-"  # private
    elif name.startswith("_"):
        if name.startswith("_abc_"):  # Special case for ABC implementation details
            return "~"  # package private
        return "#"  # protected
    return "+"  # public

def extract_method_params(item: FunctionDef) -> List[str]:
    """Extract method parameters with type hints."""
    params = []
    for arg in item.args.args:
        if arg.annotation and arg.arg != 'self':
            type_hint = extract_type_hint(arg.annotation)
            params.append(f"{arg.arg}: {type_hint}")
        elif arg.arg != 'self':
            params.append(arg.arg)
    return params

def extract_methods(node: ClassDef) -> List[tuple[str, str, str, List[str]]]:
    """Extract methods from a class definition.
    
    Returns:
        List of tuples containing (name, parameters, visibility, modifiers)
    """
    methods = []
    for item in node.body:
        if isinstance(item, FunctionDef):
            params = extract_method_params(item)
            visibility = determine_visibility(item.name)
            modifiers = []
            
            # Check for static methods
            if any(d.id == 'staticmethod' for d in item.decorator_list if isinstance(d, Name)):
                modifiers.append('static')
                
            # Check for abstract methods
            if any(d.id == 'abstractmethod' for d in item.decorator_list if isinstance(d, Name)):
                modifiers.append('abstract')
                
            # Check for classmethod (classifier in PlantUML)
            if any(d.id == 'classmethod' for d in item.decorator_list if isinstance(d, Name)):
                modifiers.append('classifier')
                
            # Join parameters if there are any, otherwise use empty string
            param_str = ", ".join(params)
            methods.append((item.name, param_str, visibility, modifiers))
    return methods

def extract_attributes(node: ClassDef) -> List[tuple[str, str, str, List[str]]]:
    """Extract attributes from a class definition.
    
    Args:
        node: The ClassDef AST node to extract attributes from
        
    Returns:
        List of tuples containing (name, type, visibility, modifiers)
    """
    from ast import AnnAssign, Assign, Name, FunctionDef
    attributes = []
    
    # First collect all attributes defined in __init__
    init_attributes = set()
    for item in node.body:
        if isinstance(item, FunctionDef) and item.name == '__init__':
            for stmt in item.body:
                if isinstance(stmt, Assign):
                    for target in stmt.targets:
                        if isinstance(target, Attribute) and isinstance(target.value, Name) and target.value.id == 'self':
                            init_attributes.add(target.attr)
                            # Add instance attributes to the list
                            visibility = determine_visibility(target.attr)
                            attributes.append((target.attr, "Any", visibility, []))
    
    # Now process class-level attributes
    for item in node.body:
        if isinstance(item, AnnAssign) and isinstance(item.target, Name):
            type_hint = extract_type_hint(item.annotation)
            visibility = determine_visibility(item.target.id)
            modifiers = []
            
            # Add the attribute if it's not already defined in __init__
            if item.target.id not in init_attributes:
                # Check if this is a static field by looking for cls.field_name in classmethods
                if is_static_field(node, item.target.id):
                    modifiers.append("static")
                attributes.append((item.target.id, type_hint, visibility, modifiers))
        elif isinstance(item, Assign):
            for target in item.targets:
                if isinstance(target, Name):
                    visibility = determine_visibility(target.id)
                    modifiers = []
                    
                    # Add the attribute if it's not already defined in __init__
                    if target.id not in init_attributes:
                        # Check if this is a static field by looking for cls.field_name in classmethods
                        if is_static_field(node, target.id):
                            modifiers.append("static")
                        attributes.append((target.id, "Any", visibility, modifiers))
    return attributes

def is_static_field(node: ClassDef, field_name: str) -> bool:
    """Determine if a field is static by checking if it's referenced in a @classmethod."""
    from ast import FunctionDef, Attribute, Name
    
    for item in node.body:
        if isinstance(item, FunctionDef):
            # Check if this is a classmethod
            if any(isinstance(d, Name) and d.id == 'classmethod' for d in item.decorator_list):
                # Look for cls.field_name in the method body
                for node in walk(item):
                    if isinstance(node, Attribute) and isinstance(node.value, Name) and node.value.id == 'cls' and node.attr == field_name:
                        return True
    return False

def parse_class_definitions(content: str, filename: str, package_base_name: Optional[str] = None) -> Dict[str, ClassInfo]:
    """Parse Python file content and extract class information.
    
    Args:
        content: The Python source code content to parse
        filename: The relative path of the file being parsed
        package_base_name: Optional base package name to prepend to module paths
    """
    try:
        tree = parse(content)
    except SyntaxError as e:
        print(f"Error parsing {filename}: {str(e)}")
        raise  # Re-raise the exception after logging

    # Extract module path from filename
    import os
    module_path = os.path.splitext(filename)[0]  # Remove .py extension
    if module_path.startswith("./") or module_path.startswith("../"):
        module_path = module_path.split("/", 1)[1]  # Remove ./ or ../
    module_path = module_path.replace("/", ".")  # Convert path separators to dots

    # Prepend package base name if provided
    if package_base_name:
        module_path = f"{package_base_name}.{module_path}"

    classes = collect_class_info(tree, module_path)
    add_composition_relationships(tree, classes)

    return classes

def collect_class_info(tree: AST, module_path: str = "") -> Dict[str, ClassInfo]:
    """Collect class information from AST, including element types and relationships."""
    classes: Dict[str, ClassInfo] = {}
    visitor = ClassRelationshipVisitor()
    visitor.visit(tree)
    
    for node in walk(tree):
        if isinstance(node, ClassDef):
            class_info = ClassInfo(node.name, module_path)
            
            # Set element type
            class_info.element_type = visitor.element_types.get(node.name, "class")
            
            # Set class visibility
            class_info.visibility = determine_class_visibility(node.name)
            
            # Set stereotype if present
            if node.name in visitor.stereotypes:
                class_info.stereotype = visitor.stereotypes[node.name]
            
            # Extract base classes from AST node
            base_classes = [base.id for base in node.bases if isinstance(base, Name)]
            
            # Transfer base classes from AST node to ClassInfo
            for base_id in base_classes:
                if base_id == 'ABC':
                    continue  # Skip ABC as it's an implementation detail
                # Add all non-ABC bases to base_classes initially
                class_info.base_classes.append(base_id)
            
            # Extract methods and attributes with their modifiers
            class_info.methods = extract_methods(node)
            class_info.attributes = extract_attributes(node)
            
            # Add relationships from visitor
            for source, target in visitor.composition_relations:
                if source == node.name:
                    class_info.composition_relationships.add(target)
            
            for source, target in visitor.aggregation_relations:
                if source == node.name:
                    class_info.aggregation_relationships.add(target)
            
            for source, target in visitor.dependency_relations:
                if source == node.name:
                    class_info.dependencies.add(target)
            
            for source, target in visitor.weak_dependency_relations:
                if source == node.name:
                    class_info.weak_dependencies.add(target)
            
            classes[node.name] = class_info
            
    # Process relationships after all classes are collected
    for class_name, class_info in classes.items():
        # Check for interface implementations
        for base in class_info.base_classes[:]:  # Create a copy to modify during iteration
            if base in classes and visitor.element_types.get(base) == "interface":
                class_info.base_classes.remove(base)
                if base not in class_info.implemented_interfaces:
                    class_info.implemented_interfaces.append(base)
    
    return classes

def add_composition_relationships(tree: AST, classes: Dict[str, ClassInfo]) -> None:
    """Add composition and other relationships to class info objects."""
    visitor = ClassRelationshipVisitor()
    visitor.visit(tree)
    
    # Add discovered relationships to the class info
    for source, target in visitor.composition_relations:
        if source in classes:
            classes[source].composition_relationships.add(target)
            
    for source, target in visitor.aggregation_relations:
        if source in classes:
            classes[source].aggregation_relationships.add(target)
            
    for source, target in visitor.dependency_relations:
        if source in classes:
            classes[source].dependencies.add(target)
            
    for source, target in visitor.weak_dependency_relations:
        if source in classes:
            classes[source].weak_dependencies.add(target)

































