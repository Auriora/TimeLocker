#!/usr/bin/env python3
"""Validate TimeLocker release identity, artifact metadata, data, and hashes."""

from __future__ import annotations

import argparse
import ast
import configparser
import hashlib
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

EXPECTED_REQUIRES_PYTHON = ">=3.12,<3.14"
EXPECTED_ENTRY_POINTS = {
    "timelocker": "TimeLocker.cli:main",
    "timelocker-system-control": "TimeLocker.system_control.backend_entry:main",
    "timelocker-tray": "TimeLocker.system_control.tray_entry:main",
    "tl": "TimeLocker.cli:main",
}


def project_metadata(root: Path) -> dict[str, object]:
    with (root / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)


def package_version(root: Path) -> str:
    module = ast.parse((root / "src/TimeLocker/__init__.py").read_text())
    for statement in module.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in statement.targets
        ):
            return str(ast.literal_eval(statement.value))
    raise AssertionError("src/TimeLocker/__init__.py does not define __version__")


def expected_package_data(root: Path, metadata: dict[str, object]) -> set[str]:
    patterns = metadata["tool"]["setuptools"]["package-data"]["TimeLocker"]  # type: ignore[index]
    package_root = root / "src/TimeLocker"
    return {
        path.relative_to(root / "src").as_posix()
        for pattern in patterns
        for path in package_root.glob(pattern)
        if path.is_file()
    }


def parse_metadata(raw: bytes) -> tuple[str, str]:
    parsed = BytesParser().parsebytes(raw)
    return str(parsed["Version"]), str(parsed["Requires-Python"])


def parse_entry_points(raw: bytes) -> dict[str, str]:
    config = configparser.ConfigParser()
    config.read_string(raw.decode())
    return dict(config["console_scripts"])


def assert_requires_python(actual: str, artifact: str) -> None:
    actual_parts = {part.strip() for part in actual.split(",")}
    expected_parts = {part.strip() for part in EXPECTED_REQUIRES_PYTHON.split(",")}
    assert actual_parts == expected_parts, (
        f"{artifact} Requires-Python is {actual}, expected {EXPECTED_REQUIRES_PYTHON}"
    )


def inspect_wheel(path: Path, expected_version: str, package_data: set[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_name = next(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        entry_points_name = next(
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        )
        version, requires_python = parse_metadata(archive.read(metadata_name))
        entry_points = parse_entry_points(archive.read(entry_points_name))
    assert version == expected_version, (
        f"wheel version is {version}, expected {expected_version}"
    )
    assert_requires_python(requires_python, "wheel")
    assert entry_points == EXPECTED_ENTRY_POINTS, (
        f"wheel entry points differ: {entry_points}"
    )
    missing = package_data - names
    assert not missing, f"wheel is missing package data: {sorted(missing)}"


def inspect_sdist(path: Path, expected_version: str, package_data: set[str]) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = {PurePosixPath(name) for name in archive.getnames()}
        pkg_info = next(
            name for name in names if len(name.parts) == 2 and name.name == "PKG-INFO"
        )
        extracted = archive.extractfile(str(pkg_info))
        assert extracted is not None
        version, requires_python = parse_metadata(extracted.read())
    assert version == expected_version, (
        f"sdist version is {version}, expected {expected_version}"
    )
    assert_requires_python(requires_python, "sdist")
    prefix = pkg_info.parent
    expected_names = {prefix / "src" / PurePosixPath(name) for name in package_data}
    missing = expected_names - names
    assert not missing, f"sdist is missing package data: {sorted(map(str, missing))}"


def write_and_verify_hashes(artifacts: list[Path], destination: Path) -> None:
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in artifacts
    ]
    destination.write_text("\n".join(lines) + "\n")
    for line, path in zip(destination.read_text().splitlines(), artifacts, strict=True):
        digest, filename = line.split("  ", maxsplit=1)
        assert filename == path.name
        assert digest == hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path, dist: Path, expected_version: str) -> None:
    metadata = project_metadata(root)
    project = metadata["project"]  # type: ignore[index]
    versions = {str(project["version"]), package_version(root)}  # type: ignore[index]
    assert versions == {expected_version}, (
        f"version guard failed: expected={expected_version}, sources={sorted(versions)}"
    )
    assert project["requires-python"] == EXPECTED_REQUIRES_PYTHON  # type: ignore[index]

    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    assert len(wheels) == 1, f"expected one wheel, found {len(wheels)}"
    assert len(sdists) == 1, f"expected one sdist, found {len(sdists)}"
    package_data = expected_package_data(root, metadata)
    assert package_data, "package-data declaration did not resolve any files"
    inspect_wheel(wheels[0], expected_version, package_data)
    inspect_sdist(sdists[0], expected_version, package_data)
    write_and_verify_hashes([*wheels, *sdists], dist / "SHA256SUMS")
    print(
        f"Validated {wheels[0].name}, {sdists[0].name}, "
        f"{len(package_data)} package-data files, and SHA-256 hashes"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-version", required=True)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--dist", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    validate(root, (args.dist or root / "dist").resolve(), args.expected_version)


if __name__ == "__main__":
    main()
