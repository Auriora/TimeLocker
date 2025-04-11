"""Main entry point for PlantUML class diagram generation."""

import argparse
import logging

from .config import ProjectConfig, PlantUMLConfig
from .plantuml_generator import generate_class_diagram

def main():
    """Main entry point with command line argument parsing."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Parse command line arguments
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