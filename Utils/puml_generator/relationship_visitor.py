"""AST visitor for extracting class relationships."""

from ast import NodeVisitor, ClassDef, Name, AST, Subscript, AnnAssign, Index, FunctionDef, Expr, Constant, Attribute, Assign, Call
from typing import Dict, Optional, Set, Tuple
from .constants import ElementType

class ClassRelationshipVisitor(NodeVisitor):
    """AST visitor that extracts class relationships and element types."""
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
        
        # # Check for interface pattern (only abstract methods)
        # has_only_abstract_methods = True
        # has_methods = False
        # for item in node.body:
        #     if isinstance(item, FunctionDef):
        #         has_methods = True
        #         if not any(d.id == 'abstractmethod' for d in item.decorator_list if isinstance(d, Name)):
        #             has_only_abstract_methods = False
        #             break
        
        # Check for interface first (has ABC and all methods are abstract)
        if is_abc:
            # Only consider it an interface if the class name contains "Interface" or has "interface" in a comment
            if "Interface" in node.name:
                self.element_types[node.name] = ElementType.INTERFACE
            else:
                self.element_types[node.name] = ElementType.ABSTRACT_CLASS
            return

        # Check for enum
        if any(base.id == 'Enum' for base in node.bases if isinstance(base, Name)):
            self.element_types[node.name] = ElementType.ENUM
            return

        # Check for dataclass/struct-like classes
        if any(d.id == 'dataclass' for d in node.decorator_list if isinstance(d, Name)):
            self.element_types[node.name] = ElementType.STRUCT
            return

        # Default to regular class
        self.element_types[node.name] = ElementType.CLASS

    def _handle_inheritance(self, node: ClassDef):
        """Handle inheritance relationships for a class."""
        # Initialize base_classes list if not present
        if not hasattr(node, 'base_classes'):
            node.base_classes = []
            
        for base in node.bases:
            if isinstance(base, Name):
                # Skip ABC as it's an implementation detail
                if base.id == 'ABC':
                    continue
                    
                # Add base class to inheritance relations
                self.inheritance_relations.add((node.name, base.id))
                
                # Add base class to the node's base_classes list
                if base.id not in node.base_classes:
                    node.base_classes.append(base.id)

    def _handle_composition(self, node: ClassDef):
        """Handle composition relationships for a class."""
        previous_class = self.current_class
        self.current_class = node.name
        
        # Look for composition relationships in class body
        for item in node.body:
            self._handle_class_body_item(item, node)
        
        self.current_class = previous_class

    def visit_FunctionDef(self, node: FunctionDef):
        """Visit a function definition and collect dependency information."""
        if self.current_class and node.name != '__init__':  # Skip __init__ as it's handled separately
            # Visit the function body to collect dependencies
            for stmt in node.body:
                if isinstance(stmt, Assign):
                    if isinstance(stmt.value, Call):
                        if isinstance(stmt.value.func, Name):
                            # Local variable instantiation indicates dependency
                            self.dependency_relations.add((self.current_class, stmt.value.func.id))
                        elif isinstance(stmt.value.func, Attribute):
                            if isinstance(stmt.value.func.value, Name):
                                self.dependency_relations.add((self.current_class, stmt.value.func.value.id))
        self.generic_visit(node)

    def _handle_class_body_item(self, item: AST, node: ClassDef):
        """Handle a single item in the class body for relationships."""
        if isinstance(item, AnnAssign):
            self._handle_annotated_assign(item, node)
        elif isinstance(item, Assign):
            self._handle_regular_assign(item, node)
        elif isinstance(item, FunctionDef):
            if item.name == '__init__':
                self._handle_init_method(item)
            else:
                self.visit_FunctionDef(item)

    def _handle_annotated_assign(self, item: AnnAssign, node: ClassDef):
        """Handle annotated assignments for relationships."""
        if not isinstance(item.target, Name):
            return

        if isinstance(item.annotation, Name):
            self._add_relationship_from_annotation(item.annotation, node, item)
        elif isinstance(item.annotation, Subscript) and isinstance(item.annotation.value, Name):
            self._add_relationship_from_subscript(item.annotation, node)

    def _handle_regular_assign(self, item: Assign, node: ClassDef):
        """Handle regular assignments for relationships."""
        for target in item.targets:
            if isinstance(target, Name):
                if isinstance(item.value, Call) and isinstance(item.value.func, Name):
                    self._add_relationship_from_call(item.value.func, node, item)
                elif isinstance(item.value, Name):
                    self.composition_relations.add((self.current_class, item.value.id))

    def _handle_init_method(self, init_node: FunctionDef):
        """Handle relationships in __init__ method."""
        # Check constructor parameters for aggregation relationships
        for arg in init_node.args.args:
            if arg.name != 'self' and hasattr(arg, 'annotation') and isinstance(arg.annotation, Name):
                self.aggregation_relations.add((self.current_class, arg.annotation.id))

        # Check method body for assignments
        for stmt in init_node.body:
            if isinstance(stmt, Assign):
                self._handle_init_assign(stmt)
            elif isinstance(stmt, AnnAssign):
                self._handle_init_annotated_assign(stmt)

    def _handle_init_assign(self, stmt: Assign):
        """Handle assignments in __init__ method."""
        for target in stmt.targets:
            if isinstance(target, Attribute) and isinstance(target.value, Name) and target.value.id == 'self':
                if isinstance(stmt.value, Call) and isinstance(stmt.value.func, Name):
                    self.composition_relations.add((self.current_class, stmt.value.func.id))

    def _handle_init_annotated_assign(self, stmt: AnnAssign):
        """Handle annotated assignments in __init__ method."""
        if not isinstance(stmt.target, Attribute) or not isinstance(stmt.target.value, Name) or stmt.target.value.id != 'self':
            return

        if isinstance(stmt.annotation, Name):
            self.composition_relations.add((self.current_class, stmt.annotation.id))
        elif isinstance(stmt.annotation, Subscript) and isinstance(stmt.annotation.value, Name):
            if isinstance(stmt.annotation.slice, Name):
                self.composition_relations.add((self.current_class, stmt.annotation.slice.id))
            elif isinstance(stmt.annotation.slice, Index) and isinstance(stmt.annotation.slice.value, Name):
                self.composition_relations.add((self.current_class, stmt.annotation.slice.value.id))

    def _add_relationship_from_annotation(self, annotation: Name, node: ClassDef, item: AnnAssign):
        """Add relationship based on type annotation."""
        comment_before = self._get_comment_before(node, item)
        if comment_before:
            if 'weak whole-part' in comment_before:
                self.aggregation_relations.add((self.current_class, annotation.id))
            elif 'weak dependency' in comment_before:
                self.weak_dependency_relations.add((self.current_class, annotation.id))
            elif 'strong dependency' in comment_before:
                self.dependency_relations.add((self.current_class, annotation.id))
            else:
                self.composition_relations.add((self.current_class, annotation.id))
        else:
            self.composition_relations.add((self.current_class, annotation.id))

    def _add_relationship_from_subscript(self, annotation: Subscript, node: ClassDef):
        """Add relationship based on subscript type annotation."""
        if isinstance(annotation.slice, Name):
            self.composition_relations.add((self.current_class, annotation.slice.id))
        elif isinstance(annotation.slice, Index) and isinstance(annotation.slice.value, Name):
            self.composition_relations.add((self.current_class, annotation.slice.value.id))

    def _add_relationship_from_call(self, func: Name, node: ClassDef, item: Assign):
        """Add relationship based on function call."""
        comment_before = self._get_comment_before(node, item)
        if comment_before:
            if 'weak whole-part' in comment_before:
                self.aggregation_relations.add((self.current_class, func.id))
            elif 'weak dependency' in comment_before:
                self.weak_dependency_relations.add((self.current_class, func.id))
            elif 'strong dependency' in comment_before:
                self.dependency_relations.add((self.current_class, func.id))
            else:
                self.composition_relations.add((self.current_class, func.id))
        else:
            self.composition_relations.add((self.current_class, func.id))

    def _get_comment_before(self, node: ClassDef, item: AST) -> Optional[str]:
        """Get the comment that appears before a node in the AST."""
        for stmt in node.body:
            if isinstance(stmt, Expr) and isinstance(stmt.value, Constant):
                comment = stmt.value.value.strip().lower()
            elif stmt == item:
                break
        return None

