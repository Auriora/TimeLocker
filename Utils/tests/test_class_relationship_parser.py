# file: test_additional_relationships.py
import unittest
import textwrap
from Utils.puml_generator import parse_class_definitions, ClassInfo


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


if __name__ == '__main__':
    unittest.main()

