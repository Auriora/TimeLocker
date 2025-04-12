"""Class information container and related functionality."""

from typing import List, Set, Tuple
from .constants import ElementType, RelationType

class ClassInfo:
    """Container for class information extracted from source code."""
    def __init__(self, name: str, module_path: str = ""):
        self.name = name
        self.module_path = module_path
        self.methods: List[Tuple[str, str, str, List[str]]] = []  # (name, parameters, visibility, modifiers)
        self.attributes: List[Tuple[str, str, str, List[str]]] = []  # (name, type, visibility, modifiers)
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
            # Sort attributes by visibility only (private first, then protected, then public)
            # Within each visibility level, maintain original order
            visibility_order = {'-': 1, '#': 2, '+': 3}
            sorted_attrs = sorted(self.attributes, key=lambda x: visibility_order[x[2]])  # x[2] is visibility
            for attr_name, attr_type, visibility, modifiers in sorted_attrs:
                prefix_modifiers = [m for m in modifiers if m in {'static', 'abstract', 'classifier'}]
                suffix_modifiers = []  # Currently empty but could be used for other modifiers in the future
                prefix = f"{{{' '.join(prefix_modifiers)}}} " if prefix_modifiers else ""
                suffix = f" {{{' '.join(suffix_modifiers)}}}" if suffix_modifiers else ""
                puml.append(f"    {visibility} {prefix}{attr_name}: {attr_type}{suffix}")
            
            # Sort methods by visibility only (private first, then protected, then public)
            # Within each visibility level, maintain original order
            sorted_methods = sorted(self.methods, key=lambda x: visibility_order[x[2]])  # x[2] is visibility
            for method_name, params, visibility, modifiers in sorted_methods:
                prefix_modifiers = [m for m in modifiers if m in {'static', 'abstract', 'classifier'}]
                suffix_modifiers = []  # Currently empty but could be used for other modifiers in the future
                prefix = f"{{{' '.join(prefix_modifiers)}}} " if prefix_modifiers else ""
                suffix = f" {{{' '.join(suffix_modifiers)}}}" if suffix_modifiers else ""
                puml.append(f"    {visibility} {prefix}{method_name}({params}){suffix}")
        puml.append("}")
        return "\n".join(puml)

    def get_relationships(self, all_classes: dict, base_classes: set) -> List[str]:
        """Get all relationships for this class."""
        relationships = []
        
        # Extension relationships (inheritance)
        for base in self.base_classes:
            if base not in base_classes and base in all_classes:
                relationships.append(f"{all_classes[base].full_name} {RelationType.EXTENSION} {self.full_name}")

        # Implementation relationships (interfaces)
        for interface in self.implemented_interfaces:
            if interface in all_classes and interface not in base_classes:
                relationships.append(f"{all_classes[interface].full_name} {RelationType.IMPLEMENTATION} {self.full_name}")

        # Composition relationships (strong whole-part)
        for composed_class in self.composition_relationships:
            if composed_class in all_classes and composed_class not in base_classes:
                relationships.append(f"{self.full_name} {RelationType.COMPOSITION} {all_classes[composed_class].full_name}")

        # Aggregation relationships (weak whole-part)
        for aggregated_class in self.aggregation_relationships:
            if aggregated_class in all_classes and aggregated_class not in base_classes:
                relationships.append(f"{self.full_name} {RelationType.AGGREGATION} {all_classes[aggregated_class].full_name}")

        # Dependencies
        for dependent in self.dependencies:
            if dependent in all_classes and dependent not in base_classes:
                relationships.append(f"{self.full_name} {RelationType.DEPENDENCY} {all_classes[dependent].full_name}")

        # Weak dependencies
        for dependent in self.weak_dependencies:
            if dependent in all_classes and dependent not in base_classes:
                relationships.append(f"{self.full_name} {RelationType.WEAK_DEPENDENCY} {all_classes[dependent].full_name}")

        return relationships




