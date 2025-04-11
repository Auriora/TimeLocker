from ast import NodeVisitor, ClassDef, Name, AST, Subscript, AnnAssign, Index, FunctionDef, parse, walk, Assign
import argparse
import logging
import os
import sys
from os.path import abspath, dirname, join
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
    def __init__(self, name: str, module_path: str = ""):
        self.name = name
        self.module_path = module_path
        self.methods: List[Tuple[str, str]] = []  # (name, parameters)
        self.attributes: List[Tuple[str, str]] = []  # (name, type)
        self.base_classes: List[str] = []
        self.composition_relationships: Set[str] = set()

    @property
    def full_name(self) -> str:
        """Get the full class name including module path."""
        if self.module_path:
            return f"{self.module_path}.{self.name}"
        return self.name

    def to_plantuml(self) -> str:
        """Convert class information to PlantUML syntax."""
        puml = [f"class {self.full_name}"]
        if self.attributes or self.methods:
            puml.append("{")
            puml.extend(f"    - {attr_name}: {attr_type}" for attr_name, attr_type in self.attributes)
            puml.extend(f"    + {method_name}({params})" for method_name, params in self.methods)
            puml.append("}")
        return "\n".join(puml)

    def get_relationships(self) -> list[str]:
        """Get all relationships for this class."""
        relationships = [f"{base} <|-- {self.full_name}" for base in self.base_classes]
        relationships.extend([f"{self.full_name} o-- {composed_class}" for composed_class in self.composition_relationships])
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
    classes: Dict[str, ClassInfo] = {}
    visitor = ClassRelationshipVisitor()
    
    for node in walk(tree):
        if isinstance(node, ClassDef):
            class_info = ClassInfo(node.name, module_path)
            
            class_info.base_classes = extract_base_classes(node)
            class_info.methods = extract_methods(node)
            class_info.attributes = extract_attributes(node)

            classes[node.name] = class_info

    # Use ClassRelationshipVisitor to detect composition relationships
    visitor.visit(tree)
    
    for class_name, composed_class in visitor.composition_relations:
        if class_name in classes:
            classes[class_name].composition_relationships.add(composed_class)
            
    return classes

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
            classes[source].composition_relationships.add(target)

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
        "skinparam classAttributeIconSize 0",
        "hide empty members",
        ""
    ]

    # Generate class declarations
    class_lines = []
    base_classes = {'Exception', 'ABC'}
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
            
        is_abstract = any(base == 'ABC' for base in class_info.base_classes)
        keyword = "abstract class" if is_abstract else "class"
        
        if class_info.attributes or class_info.methods:
            class_lines.append(f"{keyword} {class_info.full_name} {{")
            for attr_name, attr_type in sorted(class_info.attributes):
                class_lines.append(f"    - {attr_name}: {attr_type}")
            for method_name, params in sorted(class_info.methods):
                class_lines.append(f"    + {method_name}({params})")
            class_lines.append("}")
        else:
            class_lines.append(f"{keyword} {class_info.full_name}")
        class_lines.append("")

    puml_lines.extend(class_lines)

    # Generate relationships
    all_relationships = []
    for class_info in all_classes.values():
        # Inheritance relationships
        for base in class_info.base_classes:
            if base in base_classes:
                all_relationships.append(f"{base} <|-- {class_info.full_name}")
            elif base in all_classes:
                all_relationships.append(f"{all_classes[base].full_name} <|-- {class_info.full_name}")

        # Composition relationships
        for composed_class in class_info.composition_relationships:
            if composed_class in all_classes:
                all_relationships.append(f"{class_info.full_name} o-- {all_classes[composed_class].full_name}")

    # Sort and add relationships
    inheritance = sorted(r for r in set(all_relationships) if '<|--' in r)
    composition = sorted(r for r in set(all_relationships) if 'o--' in r)

    if inheritance or composition:
        puml_lines.append("")
    if inheritance:
        puml_lines.extend(inheritance)
    if composition:
        if inheritance:
            puml_lines.append("")
        puml_lines.extend(composition)

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









