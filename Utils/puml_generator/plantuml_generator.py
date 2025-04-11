"""PlantUML diagram generation functionality."""

import logging
import os
import sys
from os.path import abspath, join
from traceback import format_exc
from typing import Dict, List
from plantuml import PlantUML

from .class_info import ClassInfo
from .class_parser import parse_class_definitions
from .config import ProjectConfig, PlantUMLConfig
from .constants import RelationType

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
    all_classes = collect_all_classes(project_config)
    if not all_classes:
        return

    # Generate PlantUML content
    puml_content = generate_plantuml_content(all_classes, project_config.package_base_name)

    # Write and generate diagram
    output_file = join(project_config.output_dir, "combined_classes.puml")
    try:
        with open(output_file, 'w') as f:
            f.write(puml_content)
        logging.info(f"PlantUML file written to {output_file}")
        
        server.processes_file(abspath(output_file))
        logging.info("Class diagram generated successfully")
    except Exception as e:
        logging.error(f"Error generating PlantUML diagram: {str(e)}")
        logging.error("Make sure the PlantUML server is running and accessible.")
        sys.exit(1)

def collect_all_classes(project_config: ProjectConfig) -> Dict[str, ClassInfo]:
    """Collect class information from all Python files in the project."""
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
        return {}

    return all_classes

def generate_plantuml_content(all_classes: Dict[str, ClassInfo], package_base_name: str) -> str:
    """Generate PlantUML content from collected class information."""
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
    class_lines = generate_class_declarations(all_classes)
    puml_lines.extend(class_lines)

    # Generate relationships
    relationship_lines = generate_relationship_declarations(all_classes)
    puml_lines.extend(relationship_lines)

    # Add package information
    puml_lines.extend([
        "' Packages",
        f"package {package_base_name} <<Rectangle>> ",
        "{",
        "}",
        "",
        "@enduml"
    ])

    return "\n".join(puml_lines)

def generate_class_declarations(all_classes: Dict[str, ClassInfo]) -> List[str]:
    """Generate PlantUML class declarations."""
    class_lines = []
    base_classes = {'Exception', 'ABC', 'Enum', 'Interface'}
    
    # Skip outputting base classes since they don't add value
    
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

    return class_lines

def generate_relationship_declarations(all_classes: Dict[str, ClassInfo]) -> List[str]:
    """Generate PlantUML relationship declarations."""
    base_classes = {'Exception', 'ABC', 'Enum', 'Interface'}
    all_relationships = []
    
    # Collect all relationships
    for class_info in all_classes.values():
        if class_info.name in base_classes:
            continue
        all_relationships.extend(class_info.get_relationships(all_classes, base_classes))

    # Sort relationships by type
    extensions = sorted(r for r in set(all_relationships) if RelationType.EXTENSION in r)
    implementations = sorted(r for r in set(all_relationships) if RelationType.IMPLEMENTATION in r)
    compositions = sorted(r for r in set(all_relationships) if RelationType.COMPOSITION in r)
    aggregations = sorted(r for r in set(all_relationships) if RelationType.AGGREGATION in r)
    dependencies = sorted(r for r in set(all_relationships) if RelationType.DEPENDENCY in r)
    weak_dependencies = sorted(r for r in set(all_relationships) if RelationType.WEAK_DEPENDENCY in r)

    # Generate relationship sections
    relationship_lines = []
    if any([extensions, implementations, compositions, aggregations, dependencies, weak_dependencies]):
        relationship_lines.extend(["", "' Relationships", ""])

    if extensions:
        relationship_lines.extend(["' Extensions (inheritance)"] + extensions + [""])
    if implementations:
        relationship_lines.extend(["' Implementations"] + implementations + [""])
    if compositions:
        relationship_lines.extend(["' Compositions"] + compositions + [""])
    if aggregations:
        relationship_lines.extend(["' Aggregations"] + aggregations + [""])
    if dependencies:
        relationship_lines.extend(["' Dependencies"] + dependencies + [""])
    if weak_dependencies:
        relationship_lines.extend(["' Weak dependencies"] + weak_dependencies + [""])

    return relationship_lines