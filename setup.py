#!/usr/bin/env python3
"""
TimeLocker Setup Configuration

This setup.py file configures TimeLocker for PyPI distribution with proper
metadata, dependencies, and entry points.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements from requirements.txt
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [
                line.strip() for line in f
                if line.strip() and not line.startswith('#')
        ]
else:
    requirements = [
            "packaging>=24.2",
            "b2sdk>=2.8.0",
            "boto3>=1.37.29",
            "plantuml>=0.3.0",
            "cryptography>=44.0.1",
            "typing_extensions>=4.9.0",
    ]

# Filter out test dependencies for production install
production_requirements = [
        req for req in requirements
        if not any(test_pkg in req.lower() for test_pkg in ['pytest', 'coverage', 'mock'])
]

setup(
        # Basic package information
        name="timelocker",
        version="1.0.0",
        description="High-level Python interface for backup operations using Restic",
        long_description=long_description,
        long_description_content_type="text/markdown",

        # Author and contact information
        author="Bruce Cherrington",
        author_email="bruce.cherrington@outlook.com",
        maintainer="Bruce Cherrington",
        maintainer_email="bruce.cherrington@outlook.com",

        # Project URLs
        url="https://github.com/Auriora/TimeLocker",
        project_urls={
                "Bug Reports":   "https://github.com/Auriora/TimeLocker/issues",
                "Source":        "https://github.com/Auriora/TimeLocker",
                "Documentation": "https://github.com/Auriora/TimeLocker/tree/main/docs",
        },

        # Package discovery and structure
        package_dir={"": "src"},
        packages=find_packages(where="src"),
        include_package_data=True,

        # Dependencies
        install_requires=production_requirements,
        python_requires=">=3.12",

        # Optional dependencies for different use cases
        extras_require={
                "dev":      [
                        "pytest>=8.3.5",
                        "pytest-cov>=6.0.0",
                        "pytest-mock>=3.14.0",
                        "pytest-xdist>=3.6.0",
                        "pytest-benchmark>=4.0.0",
                ],
                "aws":      ["boto3>=1.37.29"],
                "b2":       ["b2sdk>=2.8.0"],
                "diagrams": ["plantuml>=0.3.0"],
        },

        # Entry points for CLI usage
        entry_points={
                "console_scripts": [
                        "timelocker=TimeLocker.cli:main",
                        "tl=TimeLocker.cli:main",
                ],
        },

        # Package data and additional files
        package_data={
                "TimeLocker": [
                        "restic/*.json",
                        "config/*.json",
                        "*.md",
                ],
        },

        # Classification and metadata
        classifiers=[
                # Development Status
                "Development Status :: 5 - Production/Stable",

                # Intended Audience
                "Intended Audience :: Developers",
                "Intended Audience :: System Administrators",
                "Intended Audience :: End Users/Desktop",

                # Topic
                "Topic :: System :: Archiving :: Backup",
                "Topic :: System :: Systems Administration",
                "Topic :: Software Development :: Libraries :: Python Modules",
                "Topic :: Utilities",

                # License
                "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",

                # Operating System
                "Operating System :: OS Independent",
                "Operating System :: POSIX :: Linux",
                "Operating System :: MacOS",
                "Operating System :: Microsoft :: Windows",

                # Programming Language
                "Programming Language :: Python :: 3",
                "Programming Language :: Python :: 3.12",
                "Programming Language :: Python :: 3.13",
                "Programming Language :: Python :: 3 :: Only",

                # Environment
                "Environment :: Console",
                "Environment :: No Input/Output (Daemon)",

                # Natural Language
                "Natural Language :: English",
        ],

        # Keywords for PyPI search
        keywords=[
                "backup", "restic", "archive", "storage", "cloud", "encryption",
                "deduplication", "incremental", "snapshot", "restore", "recovery",
                "aws", "s3", "backblaze", "b2", "security", "automation"
        ],

        # License
        license="GPL-3.0",

        # Zip safety
        zip_safe=False,

        # Platform compatibility
        platforms=["any"],
)
