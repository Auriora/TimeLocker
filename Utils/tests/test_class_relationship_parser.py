# file: test_additional_relationships.py
import unittest
import textwrap
from Utils.puml_generator import parse_class_definitions


class TestAdditionalRelationships(unittest.TestCase):
    def test_inheritance_relationship(self):
        """
        Test that parse_class_definitions correctly identifies
        an inheritance (implementation) relationship.
        """
        code = textwrap.dedent("""
            class Base:
                pass

            class Derived(Base):
                pass
        """)
        classes = parse_class_definitions(code, "src/test_inheritance.py")
        self.assertIn("Derived", classes, "Derived class should be parsed.")
        self.assertIn("Base", classes["Derived"].base_classes,
                      "Derived should have an inheritance relationship with Base.")

    def test_aggregation_relationship(self):
        """
        Test that parse_class_definitions correctly identifies
        an aggregation relationship when an object is passed in.
        """
        code = textwrap.dedent("""
            class Provider:
                pass

            class Consumer:
                def __init__(self, provider: Provider):
                    self.provider = provider
        """)
        classes = parse_class_definitions(code, "src/test_aggregation.py")
        self.assertIn("Consumer", classes, "Consumer class should be parsed.")
        self.assertIn("Provider", classes["Consumer"].aggregation_relationships,
                      "Consumer should have an aggregation relationship with Provider.")

    def test_dependency_relationship(self):
        """
        Test that parse_class_definitions correctly identifies
        a dependency by using a class instance within a method.
        """
        code = textwrap.dedent("""
            class Helper:
                def assist(self):
                    pass

            class Worker:
                def work(self):
                    helper = Helper()
                    helper.assist()
        """)
        classes = parse_class_definitions(code, "src/test_dependency.py")
        self.assertIn("Worker", classes, "Worker class should be parsed.")
        self.assertIn("Helper", classes["Worker"].dependencies,
                      "Worker should have a dependency relationship with Helper.")

    def test_composition_relationship(self):
        """
        Test that parse_class_definitions correctly identifies
        a composition relationship when an instance is created within __init__.
        """
        code = textwrap.dedent("""
            class ComposedPart:
                pass
            class Whole:
                def __init__(self):
                    self.part = ComposedPart()
        """)
        classes = parse_class_definitions(code, "src/test_composition.py")
        self.assertIn("Whole", classes, "Whole class should be parsed.")
        self.assertIn("ComposedPart", classes["Whole"].composition_relationships,
                      "Whole should have a composition relationship with ComposedPart.")

    def test_weak_dependency_relationship(self):
        """
        Test that parse_class_definitions correctly identifies
        a weak dependency when an instance is used conditionally.
        """
        code = textwrap.dedent("""
            class OptionalHelper:
                def assist(self):
                    pass
            class Consumer:
                def process(self):
                    # weak dependency example:
                    if False:
                        helper = OptionalHelper()
                        helper.assist()
        """)
        classes = parse_class_definitions(code, "src/test_weak_dependency.py")
        self.assertIn("Consumer", classes, "Consumer class should be parsed.")
        self.assertIn("OptionalHelper", classes["Consumer"].weak_dependencies,
                      "Consumer should have a weak dependency relationship with OptionalHelper.")

    def test_multiple_relationships(self):
        """
        Test a class with multiple relationships:
        - Inheritance from Base.
        - Composition relationship via attribute assignment.
        - Dependency relationship in a method.
        """
        code = textwrap.dedent("""
            class Base:
                pass
            class ComposedPart:
                pass
            class Helper:
                def assist(self):
                    pass
            class Consumer(Base):
                def __init__(self, provider, helper: Helper):
                    self.provider = provider  # This may be marked as aggregation if further analyzed
                    self.part = ComposedPart()
                def process(self):
                    temp = Helper()
                    temp.assist()
        """)
        classes = parse_class_definitions(code, "src/test_multiple_relationships.py")
        self.assertIn("Consumer", classes, "Consumer class should be parsed.")
        consumer = classes["Consumer"]
        # Inheritance check
        self.assertIn("Base", consumer.base_classes,
                      "Consumer should inherit from Base.")
        # Composition check
        self.assertIn("ComposedPart", consumer.composition_relationships,
                      "Consumer should have a composition relationship with ComposedPart.")
        # Dependency check (for the temporary helper instance)
        self.assertIn("Helper", consumer.dependencies,
                      "Consumer should have a dependency relationship with Helper.")
        # Optionally, if the 'provider' parameter is not recognized as a specific relationship,
        # there should be no aggregation for it unless determined by your parser:
        self.assertEqual(len(consumer.aggregation_relationships), 0,
                         "No aggregation relationship should be registered for an untyped provider by default.")

if __name__ == '__main__':
    unittest.main()

