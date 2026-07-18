"""Regression checks for the installed TimeLocker package identity."""

from pathlib import Path

import pytest


@pytest.mark.unit
def test_python_tests_do_not_import_the_source_layout_namespace():
    """Tests must exercise the same module identity used by the CLI."""
    repo_root = Path(__file__).resolve().parents[2]
    forbidden_namespace = "src" + ".TimeLocker"
    offenders = []

    for test_file in (repo_root / "tests").rglob("*.py"):
        if forbidden_namespace in test_file.read_text(encoding="utf-8"):
            offenders.append(test_file.relative_to(repo_root).as_posix())

    assert offenders == [], (
        "Python tests must import or patch TimeLocker, not the source-layout "
        f"namespace; offenders: {offenders}"
    )
