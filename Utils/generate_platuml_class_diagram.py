from ast import NodeVisitor, ClassDef, Name, AST, Subscript, AnnAssign, Index, FunctionDef, parse, walk, Assign, Call, Expr, Constant
import argparse
import logging
import os
import sys
from os.path import abspath, join
from traceback import format_exc
from typing import Dict, List, Optional, Set, Tuple
from plantuml import PlantUML

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PlantUMLConfig:
    """Configuration for PlantUML server and diagram settings."""
    def __init__(self, 
                 server_url: str = 'http://www.plantuml.com/plantuml/svg/',
                 basic_auth: Optional[dict] = None,
                 form_auth: Optional[dict] = None,
                 http_opts: Optional[dict] = None,
                 request_opts: Optional[dict] = None):
        self.server_url = server_url
        self.basic_auth = basic_auth or {}
        self.form_auth = form_auth or {}
        self.http_opts = http_opts or {}
        self.request_opts = request_opts or {}

class ProjectConfig:
    """Configuration for project paths and settings."""
    def __init__(self,
                 src_dir: str,
                 output_dir: str,
                 excluded_dirs: Optional[List[str]] = None,
                 package_base_name: Optional[str] = None):
        self.src_dir = abspath(src_dir)
        self.output_dir = abspath(output_dir)
        self.excluded_dirs = excluded_dirs or []
        self.package_base_name = package_base_name

    def ensure_output_dir(self) -> None:
        """Ensure output directory exists."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

class ClassRelationshipVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.classes: Dict[str, ClassDef] = {}  # Maps class names to their AST nodes
        self.inheritance_relations: Set[Tuple[str, str]] = set()
        self.interface_relations: Set[Tuple[str, str]] = set()
        self.composition_relations: Set[Tuple[str, str]] = set()
        self.aggregation_relations: Set[Tuple[str, str]] = set()
        self.dependency_relations: Set[Tuple[str, str]] = set()
        self.weak_dependency_relations: Set[Tuple[str, str]] = set()
        self.current_class: Optional[str] = None
        self.element_types: Dict[str, str] = {}  # Maps class name to element type
        self.stereotypes: Dict[str, str] = {}  # Maps class name to stereotype

    def visit_ClassDef(self, node: ClassDef):
        """Visit a class definition and collect information."""
        # Initialize base_classes list for the node
        node.base_classes = []
        self.classes[node.name] = node
        self._handle_inheritance(node)
        self._handle_composition(node)
        self._determine_element_type(node)
        self._handle_stereotypes(node)
        self.generic_visit(node)

    def _handle_stereotypes(self, node: ClassDef):
        """Extract stereotypes from class decorators."""
        for decorator in node.decorator_list:
            if isinstance(decorator, Name) and decorator.id == 'stereotype':
                self.stereotypes[node.name] = decorator.args[0].value if decorator.args else None
            elif isinstance(decorator, Call) and isinstance(decorator.func, Name) and decorator.func.id == 'stereotype':
                if decorator.args:
                    self.stereotypes[node.name] = decorator.args[0].value

    def _determine_element_type(self, node: ClassDef):
        """Determine the element type based on class definition and decorators."""
        # Check for exception by inheritance or name first
        is_exception = any(base.id == 'Exception' for base in node.bases if isinstance(base, Name))
        is_error_base = any(base.id.endswith('Error') for base in node.bases if isinstance(base, Name))
        has_error_name = 'Error' in node.name or 'Exception' in node.name
        
        if is_exception or is_error_base or has_error_name:
            self.element_types[node.name] = ElementType.EXCEPTION
            return

        # Check for ABC (Abstract Base Class)
        is_abc = any(base.id == 'ABC' for base in node.bases if isinstance(base, Name))
        
        # Check for interface pattern (only abstract methods)
        has_only_abstract_methods = True
        has_methods = False
        for item in node.body:
            if isinstance(item, FunctionDef):
                has_methods = True
                if not any(d.id == 'abstractmethod' for d in item.decorator_list if isinstance(d, Name)):
                    has_only_abstract_methods = False
                    break
        
        # A class is an interface if:
        # 1. It inherits from ABC and has only abstract methods
        # 2. It has at least one method and all methods are abstract
        # 3. Or if it's named Interface
        if (is_abc and has_methods and has_only_abstract_methods) or node.name == 'Interface':
            self.element_types[node.name] = ElementType.INTERFACE
            return

        # Check for enum
        if any(base.id == 'Enum' for base in node.bases if isinstance(base, Name)):
            self.element_types[node.name] = ElementType.ENUM
            return

        # Check for dataclass/struct-like classes
        if any(d.id == 'dataclass' for d in node.decorator_list if isinstance(d, Name)):
            self.element_types[node.name] = ElementType.STRUCT
            return

        # Check for abstract class (has ABC but not all methods are abstract)
        if is_abc:
            self.element_types[node.name] = ElementType.ABSTRACT_CLASS
            return

        # Default to regular class
        self.element_types[node.name] = ElementType.CLASS

    def _handle_inheritance(self, node: ClassDef):
        """Handle inheritance relationships for a class."""
        for base in node.bases:
            if isinstance(base, Name):
                # Add base class to inheritance relations
                self.inheritance_relations.add((node.name, base.id))
                
                # Add base class to the node's base_classes list
                if not hasattr(node, 'base_classes'):
                    node.base_classes = []
                if base.id not in node.base_classes:
                    node.base_classes.append(base.id)

    def _handle_composition(self, node: ClassDef):
        """Handle composition relationships for a class."""
        previous_class = self.current_class
        self.current_class = node.name
        
        # Look for composition relationships in class body
        for item in node.body:
            # Check type annotations for composition and other relationships
            if isinstance(item, AnnAssign) and isinstance(item.target, Name):
                if isinstance(item.annotation, Name):
                    # Check for relationship type based on comments or naming
                    if any(c.value.value.strip().lower().startswith('weak whole-part') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                        self.aggregation_relations.add((self.current_class, item.annotation.id))
                    elif any(c.value.value.strip().lower().startswith('weak dependency') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                        self.weak_dependency_relations.add((self.current_class, item.annotation.id))
                    elif any(c.value.value.strip().lower().startswith('strong dependency') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                        self.dependency_relations.add((self.current_class, item.annotation.id))
                    else:
                        self.composition_relations.add((self.current_class, item.annotation.id))
                elif isinstance(item.annotation, Subscript) and isinstance(item.annotation.value, Name):
                    if isinstance(item.annotation.slice, Name):
                        self.composition_relations.add((self.current_class, item.annotation.slice.id))
                    elif isinstance(item.annotation.slice, Index) and isinstance(item.annotation.slice.value, Name):
                        self.composition_relations.add((self.current_class, item.annotation.slice.value.id))
            
            # Check assignments for composition
            elif isinstance(item, Assign):
                for target in item.targets:
                    if isinstance(target, Name):
                        if isinstance(item.value, Call) and isinstance(item.value.func, Name):
                            # Check for relationship type based on comments or naming
                            if any(c.value.value.strip().lower().startswith('weak whole-part') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                                self.aggregation_relations.add((self.current_class, item.value.func.id))
                            elif any(c.value.value.strip().lower().startswith('weak dependency') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                                self.weak_dependency_relations.add((self.current_class, item.value.func.id))
                            elif any(c.value.value.strip().lower().startswith('strong dependency') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                                self.dependency_relations.add((self.current_class, item.value.func.id))
                            else:
                                self.composition_relations.add((self.current_class, item.value.func.id))
                        elif isinstance(item.value, Name):
                            # Handle direct assignments of type references
                            self.composition_relations.add((self.current_class, item.value.id))
        
        self.current_class = previous_class

    def _add_relationship(self, type_node: AST, relationship_type: str):
        """Add a relationship based on type hints and usage patterns."""
        if isinstance(type_node, Name):
            target_class = type_node.id
        elif isinstance(type_node, Subscript) and isinstance(type_node.value, Name):
            if isinstance(type_node.slice, Name):
                target_class = type_node.slice.id
            else:
                return
        else:
            return

        if relationship_type == "composition":
            self.composition_relations.add((self.current_class, target_class))
        elif relationship_type == "aggregation":
            self.aggregation_relations.add((self.current_class, target_class))
        elif relationship_type == "dependency":
            self.dependency_relations.add((self.current_class, target_class))
        elif relationship_type == "weak_dependency":
            self.weak_dependency_relations.add((self.current_class, target_class))

    def visit_AnnAssign(self, node: AnnAssign):
        """Handle type annotations for relationships."""
        if not self.current_class:
            return

        # Extract the type name from the annotation
        type_name = None
        if isinstance(node.annotation, Name):
            type_name = node.annotation.id
        elif isinstance(node.annotation, Subscript) and isinstance(node.annotation.value, Name):
            if isinstance(node.annotation.slice, Name):
                type_name = node.annotation.slice.id
            elif isinstance(node.annotation.slice, Index) and isinstance(node.annotation.slice.value, Name):
                type_name = node.annotation.slice.value.id

        if type_name:
            # Add composition relationship
            self.composition_relations.add((self.current_class, type_name))

class ElementType:
    """Supported PlantUML element types."""
    ABSTRACT = "abstract"
    ABSTRACT_CLASS = "abstract class"
    ANNOTATION = "annotation"
    CIRCLE = "circle"
    CIRCLE_SHORT = "()"
    CLASS = "class"
    CLASS_STEREO = "class"  # Used with stereotype
    DIAMOND = "diamond"
    DIAMOND_SHORT = "<>"
    ENTITY = "entity"
    ENUM = "enum"
    EXCEPTION = "exception"
    INTERFACE = "interface"
    METACLASS = "metaclass"
    PROTOCOL = "protocol"
    STEREOTYPE = "stereotype"
    STRUCT = "struct"

class RelationType:
    """Supported PlantUML relationship types."""
    EXTENSION = "<|--"  # Specialization/inheritance
    IMPLEMENTATION = "<|.."  # Interface implementation
    COMPOSITION = "*--"  # Strong whole-part relationship
    AGGREGATION = "o--"  # Weak whole-part relationship
    DEPENDENCY = "-->"  # Strong dependency
    WEAK_DEPENDENCY = "..>"  # Weak dependency

class ClassInfo:
    def __init__(self, name: str, module_path: str = ""):
        self.name = name
        self.module_path = module_path
        self.methods: List[Tuple[str, str]] = []  # (name, parameters)
        self.attributes: List[Tuple[str, str]] = []  # (name, type)
        self.base_classes: List[str] = []  # List of base class names
        self.implemented_interfaces: List[str] = []  # For interface implementations
        self.composition_relationships: Set[str] = set()  # Strong whole-part
        self.aggregation_relationships: Set[str] = set()  # Weak whole-part
        self.dependencies: Set[str] = set()  # Strong dependencies
        self.weak_dependencies: Set[str] = set()  # Weak dependencies
        self.element_type = ElementType.CLASS  # Default type
        self.stereotype = None  # Optional stereotype

    @property
    def full_name(self) -> str:
        """Get the full class name including module path and stereotype if present."""
        base_name = f"{self.module_path}.{self.name}" if self.module_path else self.name
        if self.stereotype:
            return f'{base_name} <<{self.stereotype}>>'
        return base_name

    def to_plantuml(self) -> str:
        """Convert class information to PlantUML syntax."""
        puml = [f"{self.element_type} {self.full_name} {{"]
        if self.attributes or self.methods:
            puml.extend(f"    - {attr_name}: {attr_type}" for attr_name, attr_type in self.attributes)
            puml.extend(f"    + {method_name}({params})" for method_name, params in self.methods)
        puml.append("}")
        return "\n".join(puml)

    def get_relationships(self) -> list[str]:
        """Get all relationships for this class."""
        relationships = []
        
        # Inheritance/extension relationships
        relationships.extend([f"{base} {RelationType.EXTENSION} {self.full_name}" for base in self.base_classes])
        
        # Interface implementation relationships
        relationships.extend([f"{interface} {RelationType.IMPLEMENTATION} {self.full_name}" for interface in self.implemented_interfaces])
        
        # Composition relationships (strong whole-part)
        relationships.extend([f"{self.full_name} {RelationType.COMPOSITION} {composed_class}" for composed_class in self.composition_relationships])
        
        # Aggregation relationships (weak whole-part)
        relationships.extend([f"{self.full_name} {RelationType.AGGREGATION} {aggregated_class}" for aggregated_class in self.aggregation_relationships])
        
        # Strong dependencies
        relationships.extend([f"{self.full_name} {RelationType.DEPENDENCY} {dependent}" for dependent in self.dependencies])
        
        # Weak dependencies
        relationships.extend([f"{self.full_name} {RelationType.WEAK_DEPENDENCY} {dependent}" for dependent in self.weak_dependencies])
        
        return relationships


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
            class_info.element_type = visitor.element_types.get(node.name, ElementType.CLASS)
            
            # Set stereotype if present
            if node.name in visitor.stereotypes:
                class_info.stereotype = visitor.stereotypes[node.name]
            
            # Extract base classes from AST node
            base_classes = [base.id for base in node.bases if isinstance(base, Name)]
            
            # Transfer base classes from AST node to ClassInfo
            for base_id in base_classes:
                if base_id in visitor.classes and visitor.element_types.get(base_id) == ElementType.INTERFACE:
                    class_info.implemented_interfaces.append(base_id)
                else:
                    class_info.base_classes.append(base_id)
            
            # Extract methods and attributes
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
        for interface in class_info.base_classes[:]:  # Create a copy to modify during iteration
            if interface in classes and classes[interface].element_type == ElementType.INTERFACE:
                class_info.base_classes.remove(interface)
                class_info.implemented_interfaces.append(interface)
    
    return classes

def extract_base_classes(node: ClassDef) -> List[str]:
    """Extract base classes from a ClassDef node.
    
    This function handles both the case where base_classes is already stored in the node
    and where we need to extract it from the bases attribute.
    """
    if hasattr(node, 'base_classes'):
        return node.base_classes
    return [base.id for base in node.bases if isinstance(base, Name)]

def extract_methods(node: ClassDef) -> List[Tuple[str, str]]:
    methods = []
    for item in node.body:
        if isinstance(item, FunctionDef):
            params = extract_method_params(item)
            methods.append((item.name, ", ".join(params)))
    return methods

def extract_method_params(item: FunctionDef) -> List[str]:
    params = []
    for arg in item.args.args:
        if arg.annotation and arg.arg != 'self':
            type_hint = extract_type_hint(arg.annotation)
            params.append(f"{arg.arg}: {type_hint}")
        elif arg.arg != 'self':
            params.append(arg.arg)
    return params

def extract_attributes(node: ClassDef) -> List[Tuple[str, str]]:
    attributes = []
    for item in node.body:
        if isinstance(item, AnnAssign) and isinstance(item.target, Name):
            type_hint = extract_type_hint(item.annotation)
            attributes.append((item.target.id, type_hint))
        elif isinstance(item, Assign):
            for target in item.targets:
                if isinstance(target, Name):
                    attributes.append((target.id, "Any"))
    return attributes

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
            
    # Also check for relationships through type annotations and assignments
    for node in walk(tree):
        if isinstance(node, ClassDef) and node.name in classes:
            for item in node.body:
                # Check type annotations
                if isinstance(item, AnnAssign) and isinstance(item.target, Name):
                    if isinstance(item.annotation, Name):
                        # Check for relationship type based on comments
                        if any(c.value.value.strip().lower().startswith('weak whole-part') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                            classes[node.name].aggregation_relationships.add(item.annotation.id)
                        elif any(c.value.value.strip().lower().startswith('weak dependency') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                            classes[node.name].weak_dependencies.add(item.annotation.id)
                        elif any(c.value.value.strip().lower().startswith('strong dependency') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                            classes[node.name].dependencies.add(item.annotation.id)
                        else:
                            classes[node.name].composition_relationships.add(item.annotation.id)
                    elif isinstance(item.annotation, Subscript) and isinstance(item.annotation.value, Name):
                        if isinstance(item.annotation.slice, Name):
                            classes[node.name].composition_relationships.add(item.annotation.slice.id)
                        elif isinstance(item.annotation.slice, Index) and isinstance(item.annotation.slice.value, Name):
                            classes[node.name].composition_relationships.add(item.annotation.slice.value.id)
                
                # Check assignments
                elif isinstance(item, Assign):
                    for target in item.targets:
                        if isinstance(target, Name) and isinstance(item.value, Call):
                            if isinstance(item.value.func, Name):
                                # Check for relationship type based on comments
                                if any(c.value.value.strip().lower().startswith('weak whole-part') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                                    classes[node.name].aggregation_relationships.add(item.value.func.id)
                                elif any(c.value.value.strip().lower().startswith('weak dependency') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                                    classes[node.name].weak_dependencies.add(item.value.func.id)
                                elif any(c.value.value.strip().lower().startswith('strong dependency') for c in node.body if isinstance(c, Expr) and isinstance(c.value, Constant)):
                                    classes[node.name].dependencies.add(item.value.func.id)
                                else:
                                    classes[node.name].composition_relationships.add(item.value.func.id)

def generate_class_diagram(project_config: ProjectConfig, plantuml_config: PlantUMLConfig) -> None:
    """Generate class diagram from Python source files."""
    logging.info("Starting class diagram generation...")
    
    # Create PlantUML server instance
    server = PlantUML(url=plantuml_config.server_url,
                     basic_auth=plantuml_config.basic_auth,
                     form_auth=plantuml_config.form_auth,
                     http_opts=plantuml_config.http_opts,
                     request_opts=plantuml_config.request_opts)

    # Ensure output directory exists
    project_config.ensure_output_dir()

    # Process all Python files
    all_classes: Dict[str, ClassInfo] = {}
    try:
        for root, dirs, files in os.walk(project_config.src_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in project_config.excluded_dirs]
            
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()

                        # Get relative path from src directory for module path
                        rel_path = os.path.relpath(file_path, project_config.src_dir)
                        file_classes = parse_class_definitions(content, rel_path, project_config.package_base_name)
                        all_classes.update(file_classes)
                    except Exception as e:
                        logging.error(f"Error processing file {file_path}: {str(e)}")
                        logging.debug(format_exc())
                        continue

    except Exception as e:
        logging.error(f"Error walking through directory structure: {str(e)}")
        return

    # Initialize PlantUML content
    puml_lines = [
        "@startuml",
        "' PlantUML style configuration",
        "skinparam classAttributeIconSize 0",
        "hide empty members",
        "",
        "' Project classes",
        ""
    ]

    # Generate class declarations
    class_lines = []
    base_classes = {'Exception', 'ABC', 'Enum', 'Interface'}
    used_bases = sorted(base for base in base_classes
                       if any(base in c.base_classes for c in all_classes.values()))

    # Output used base classes
    for base in used_bases:
        class_lines.append(f"class {base}")
        class_lines.append("")

    # Output all other classes alphabetically
    sorted_classes = sorted(all_classes.values(), key=lambda x: x.full_name)
    for class_info in sorted_classes:
        if class_info.name in base_classes:
            continue

        # Use the element type already stored in class_info
        element_type = class_info.element_type
        
        if class_info.attributes or class_info.methods:
            class_lines.append(f"{element_type} {class_info.full_name} {{")
            for attr_name, attr_type in sorted(class_info.attributes):
                class_lines.append(f"    - {attr_name}: {attr_type}")
            for method_name, params in sorted(class_info.methods):
                class_lines.append(f"    + {method_name}({params})")
            class_lines.append("}")
        else:
            class_lines.append(f"{element_type} {class_info.full_name}")
        class_lines.append("")

    puml_lines.extend(class_lines)

    # Generate relationships
    all_relationships = []
    for class_info in all_classes.values():
        # Extension relationships (inheritance)
        for base in class_info.base_classes:
            if base in base_classes:
                all_relationships.append(f"{base} {RelationType.EXTENSION} {class_info.full_name}")
            elif base in all_classes:
                all_relationships.append(f"{all_classes[base].full_name} {RelationType.EXTENSION} {class_info.full_name}")

        # Implementation relationships (interfaces)
        for interface in class_info.implemented_interfaces:
            if interface in all_classes:
                all_relationships.append(f"{all_classes[interface].full_name} {RelationType.IMPLEMENTATION} {class_info.full_name}")

        # Composition relationships (strong whole-part)
        for composed_class in class_info.composition_relationships:
            if composed_class in all_classes:
                all_relationships.append(f"{class_info.full_name} {RelationType.COMPOSITION} {all_classes[composed_class].full_name}")

        # Aggregation relationships (weak whole-part)
        for aggregated_class in class_info.aggregation_relationships:
            if aggregated_class in all_classes:
                all_relationships.append(f"{class_info.full_name} {RelationType.AGGREGATION} {all_classes[aggregated_class].full_name}")

        # Dependencies
        for dependent in class_info.dependencies:
            if dependent in all_classes:
                all_relationships.append(f"{class_info.full_name} {RelationType.DEPENDENCY} {all_classes[dependent].full_name}")

        # Weak dependencies
        for dependent in class_info.weak_dependencies:
            if dependent in all_classes:
                all_relationships.append(f"{class_info.full_name} {RelationType.WEAK_DEPENDENCY} {all_classes[dependent].full_name}")

    # Sort and add relationships by type
    extensions = sorted(r for r in set(all_relationships) if RelationType.EXTENSION in r)
    implementations = sorted(r for r in set(all_relationships) if RelationType.IMPLEMENTATION in r)
    compositions = sorted(r for r in set(all_relationships) if RelationType.COMPOSITION in r)
    aggregations = sorted(r for r in set(all_relationships) if RelationType.AGGREGATION in r)
    dependencies = sorted(r for r in set(all_relationships) if RelationType.DEPENDENCY in r)
    weak_dependencies = sorted(r for r in set(all_relationships) if RelationType.WEAK_DEPENDENCY in r)

    # Add relationships with headers
    if any([extensions, implementations, compositions, aggregations, dependencies, weak_dependencies]):
        puml_lines.append("")
        puml_lines.append("' Relationships")
        puml_lines.append("")

    if extensions:
        puml_lines.append("' Extensions (inheritance)")
        puml_lines.extend(extensions)
        puml_lines.append("")

    if implementations:
        puml_lines.append("' Implementations")
        puml_lines.extend(implementations)
        puml_lines.append("")

    if compositions:
        puml_lines.append("' Compositions")
        puml_lines.extend(compositions)
        puml_lines.append("")

    if aggregations:
        puml_lines.append("' Aggregations")
        puml_lines.extend(aggregations)
        puml_lines.append("")

    if dependencies:
        puml_lines.append("' Dependencies")
        puml_lines.extend(dependencies)
        puml_lines.append("")

    if weak_dependencies:
        puml_lines.append("' Weak dependencies")
        puml_lines.extend(weak_dependencies)
        puml_lines.append("")

    puml_lines.append("' Packages")
    puml_lines.append(f"package {project_config.package_base_name} <<Rectangle>> ")
    puml_lines.append("{")
    puml_lines.append("}")
    puml_lines.append("")

    puml_lines.extend(["", "@enduml"])
    combined_puml_content = "\n".join(puml_lines)

    # Write and generate diagram
    output_file = join(project_config.output_dir, "combined_classes.puml")
    try:
        with open(output_file, 'w') as f:
            f.write(combined_puml_content)
        logging.info(f"PlantUML file written to {output_file}")
        
        server.processes_file(abspath(output_file))
        logging.info("Class diagram generated successfully")
    except Exception as e:
        logging.error(f"Error generating PlantUML diagram: {str(e)}")
        logging.error("Make sure the PlantUML server is running and accessible.")
        sys.exit(1)

def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Generate PlantUML class diagrams from Python source code.')
    parser.add_argument('--src-dir', default='src',
                       help='Source directory containing Python files (default: src)')
    parser.add_argument('--output-dir', default='docs/diagrams',
                       help='Output directory for diagrams (default: docs/diagrams)')
    parser.add_argument('--plantuml-server', default='http://www.plantuml.com/plantuml/svg/',
                       help='PlantUML server URL (default: http://www.plantuml.com/plantuml/svg/)')
    parser.add_argument('--exclude-dirs', nargs='*', default=['__pycache__'],
                       help='Directories to exclude (default: __pycache__)')
    parser.add_argument('--package-base-name',
                       help='Base package name to prepend to module paths (e.g., "myproject")')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create configurations
    project_config = ProjectConfig(
        src_dir=args.src_dir,
        output_dir=args.output_dir,
        excluded_dirs=args.exclude_dirs,
        package_base_name=args.package_base_name
    )

    plantuml_config = PlantUMLConfig(
        server_url=args.plantuml_server
    )

    # Generate diagram
    generate_class_diagram(project_config, plantuml_config)

if __name__ == '__main__':
    main()





















































