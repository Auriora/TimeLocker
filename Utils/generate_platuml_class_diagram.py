from ast import NodeVisitor, ClassDef, Name, AST, Subscript, AnnAssign, Index, FunctionDef, parse, walk, Assign
import os
import sys
from os.path import abspath
from typing import Dict, List, Set, Tuple
from plantuml import PlantUML

class ClassRelationshipVisitor(NodeVisitor):
    def __init__(self):
        self.classes: Dict[str, ClassDef] = {}
        self.inheritance_relations: Set[Tuple[str, str]] = set()
        self.composition_relations: Set[Tuple[str, str]] = set()
        self.current_class: str = None

    def visit_ClassDef(self, node: ClassDef):
        self.classes[node.name] = node
        self._handle_inheritance(node)
        self._handle_composition(node)

    def _handle_inheritance(self, node: ClassDef):
        for base in node.bases:
            if isinstance(base, Name):
                self.inheritance_relations.add((node.name, base.id))

    def _handle_composition(self, node: ClassDef):
        previous_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = previous_class

    def _add_composition_relation(self, type_node: AST):
        if isinstance(type_node, Name):
            self.composition_relations.add((self.current_class, type_node.id))
        elif isinstance(type_node, Subscript) and isinstance(type_node.value, Name):
            if isinstance(type_node.slice, Name):
                self.composition_relations.add((self.current_class, type_node.slice.id))

    def visit_AnnAssign(self, node: AnnAssign):
        # Handle type annotations for composition
        if self.current_class:
            self._add_composition_relation(node.annotation)

class ClassInfo:
    def __init__(self, name: str):
        self.name = name
        self.methods: List[Tuple[str, str]] = []  # (name, parameters)
        self.attributes: List[Tuple[str, str]] = []  # (name, type)
        self.base_classes: List[str] = []
        self.composition_relationships: Set[str] = set()

    def to_plantuml(self) -> str:
        """Convert class information to PlantUML syntax."""
        puml = [f"class {self.name}"]
        if self.attributes or self.methods:
            puml.append("{")
            puml.extend(f"    - {attr_name}: {attr_type}" for attr_name, attr_type in self.attributes)
            puml.extend(f"    + {method_name}({params})" for method_name, params in self.methods)
            puml.append("}")
        return "\n".join(puml)

    def get_relationships(self) -> list[str]:
        """Get all relationships for this class."""
        relationships = [f"{base} <|-- {self.name}" for base in self.base_classes]
        relationships.extend([f"{self.name} o-- {composed_class}" for composed_class in self.composition_relationships])
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


def parse_class_definitions(content: str, filename: str) -> Dict[str, ClassInfo]:
    """Parse Python file content and extract class information."""
    try:
        tree = parse(content)
    except SyntaxError as e:
        print(f"Error parsing {filename}: {str(e)}")
        raise  # Re-raise the exception after logging

    classes = collect_class_info(tree)
    add_composition_relationships(tree, classes)

    return classes

def collect_class_info(tree: AST) -> Dict[str, ClassInfo]:
    classes: Dict[str, ClassInfo] = {}
    visitor = ClassRelationshipVisitor()
    
    for node in walk(tree):
        if isinstance(node, ClassDef):
            class_info = ClassInfo(node.name)
            
            class_info.base_classes = extract_base_classes(node)
            class_info.methods = extract_methods(node)
            class_info.attributes = extract_attributes(node)

            classes[node.name] = class_info

    # Use ClassRelationshipVisitor to detect composition relationships
    visitor.visit(tree)
    
    for class_name, composed_class in visitor.composition_relations:
        if class_name in classes:
            classes[class_name].composition_relationships.add(composed_class)

def extract_base_classes(node: ClassDef) -> List[str]:
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
    visitor = ClassRelationshipVisitor()
    visitor.visit(tree)
    
    # Add discovered composition relationships to the class info
    for source, target in visitor.composition_relations:
        if source in classes and target in classes:
            classes[source].relationships.append(f"{source} *-- {target}")

# Create a PlantUML server instance
server = PlantUML(url='http://www.plantuml.com/plantuml/svg/',  # Using SVG format for better quality
                  basic_auth={},
                  form_auth={},
                  http_opts={},
                  request_opts={})

# Directory containing your Python files
project_dir = "../"  # Current directory, modify as needed
src_dir = f"{project_dir}/src"

# Create output directory for diagrams if it doesn't exist
output_dir = f"{project_dir}/docs/diagrams"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Create a combined PlantUML file for all classes
combined_puml_content = """@startuml
skinparam classAttributeIconSize 0
"""

# Process all Python files
all_classes: Dict[str, ClassInfo] = {}

try:
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                # Read the Python file
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()

                    # Extract class definitions without file grouping
                    file_classes = parse_class_definitions(content, file)
                    all_classes.update(file_classes)
                except Exception as e:
                    print(f"Error processing file {file_path}: {str(e)}")
                    continue

except Exception as e:
    print(f"Error walking through directory structure: {str(e)}")

# Initialize PlantUML content list with proper ordering:
# 1. Header & styling
# 2. Base classes
# 3. All class definitions
# 4. All relationships
puml_lines = []

# Start with header and minimal styling
puml_lines.extend([
    "@startuml",
    "skinparam classAttributeIconSize 0",
    "hide empty members",
    "",
])

# STEP 1: Sort and generate class declarations
class_lines = []

# Start with built-in base classes that are actually used as bases
base_classes = {'Exception', 'ABC'}
used_bases = sorted(base for base in base_classes 
                   if any(base in c.base_classes for c in all_classes.values()))

# Output used base classes first
for base in used_bases:
    class_lines.append(f"class {base}")
    class_lines.append("")

# Then output all other classes alphabetically
sorted_classes = sorted(all_classes.values(), key=lambda x: x.name)
for class_info in sorted_classes:
    # Skip if this is one of our known base classes
    if class_info.name in base_classes:
        continue
        
    # Determine if class is abstract
    is_abstract = any(base == 'ABC' for base in class_info.base_classes)
    keyword = "abstract class" if is_abstract else "class"
    
    # Output class declaration
    if class_info.attributes or class_info.methods:
        class_lines.append(f"{keyword} {class_info.name} {{")
        # Output sorted attributes
        for attr_name, attr_type in sorted(class_info.attributes):
            class_lines.append(f"    - {attr_name}: {attr_type}")
        # Output sorted methods
        for method_name, params in sorted(class_info.methods):
            class_lines.append(f"    + {method_name}({params})")
        class_lines.append("}")
    else:
        class_lines.append(f"{keyword} {class_info.name}")
    class_lines.append("")  # Empty line after each class

# First add all class declarations
puml_lines.extend(class_lines)

# Then collect all relationships from all classes
all_relationships = []
for class_info in all_classes.values():
    all_relationships.extend(class_info.get_relationships())

# Sort relationships by type (inheritance first, then composition)
inheritance = sorted(r for r in set(all_relationships) if '<|--' in r)
composition = sorted(r for r in set(all_relationships) if 'o--' in r)

# Add relationships after class definitions with proper spacing
if inheritance or composition:
    puml_lines.append("")  # Add spacing between classes and relationships
    
if inheritance:
    puml_lines.extend(inheritance)
    
if composition:
    if inheritance:
        puml_lines.append("")  # Add spacing between inheritance and composition
    puml_lines.extend(composition)

# Close the diagram
puml_lines.append("")
puml_lines.append("@enduml")

# Join all lines with newlines
combined_puml_content = "\n".join(puml_lines)

# Write the combined PlantUML content to a file
output_file = os.path.join(output_dir, "combined_classes.puml")
with open(output_file, 'w') as f:
    f.write(combined_puml_content)

# Generate the diagram
try:
    server.processes_file(abspath(output_file))
except Exception as e:
    print(f"Error generating PlantUML diagram: {str(e)}")
    print("Make sure the PlantUML server is running and accessible.")
    sys.exit(1)
