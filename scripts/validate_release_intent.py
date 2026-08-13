#!/usr/bin/env python3
"""Validate a proposed release tag against TimeLocker's version sources."""

from __future__ import annotations

import argparse
import ast
import re
import tomllib
from pathlib import Path

TAG_PATTERN = re.compile(
    r"^v(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))$"
)


def package_version(root: Path) -> str:
    module = ast.parse((root / "src/TimeLocker/__init__.py").read_text())
    for statement in module.body:
        if (
            isinstance(statement, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__version__"
                for target in statement.targets
            )
        ):
            return str(ast.literal_eval(statement.value))
    raise AssertionError("src/TimeLocker/__init__.py does not define __version__")


def validate(root: Path, version_ref: str) -> str:
    match = TAG_PATTERN.fullmatch(version_ref)
    if match is None:
        raise AssertionError(
            f"release reference must be a semantic version tag such as v0.9.1: {version_ref}"
        )

    expected = match.group("version")
    with (root / "pyproject.toml").open("rb") as stream:
        project_version = str(tomllib.load(stream)["project"]["version"])
    source_version = package_version(root)
    versions = {project_version, source_version}
    if versions != {expected}:
        raise AssertionError(
            f"version guard failed: tag={expected}, sources={sorted(versions)}"
        )
    return expected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-ref", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        version = validate(args.root.resolve(), args.version_ref)
    except AssertionError as error:
        raise SystemExit(str(error)) from error
    print(f"Release intent verified for v{version}")


if __name__ == "__main__":
    main()
