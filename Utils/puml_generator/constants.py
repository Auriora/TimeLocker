"""Constants for PlantUML diagram generation."""

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