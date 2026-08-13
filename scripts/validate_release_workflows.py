#!/usr/bin/env python3
"""Enforce TimeLocker's read-only rehearsal and publication permission boundary."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FORBIDDEN_REHEARSAL_ACTIONS = (
    "gh release create",
    "git commit",
    "git push",
    "git tag",
    "twine upload",
    "pypa/gh-action-pypi-publish",
)


def validate(rehearsal_path: Path, release_path: Path) -> None:
    rehearsal = rehearsal_path.read_text()
    release = release_path.read_text()

    assert "workflow_call:" in rehearsal, "rehearsal must be reusable"
    assert "workflow_dispatch:" in rehearsal, "rehearsal must support manual execution"
    assert re.search(r"^permissions:\n  contents: read$", rehearsal, re.MULTILINE), (
        "rehearsal must declare read-only contents permission"
    )
    for action in FORBIDDEN_REHEARSAL_ACTIONS:
        assert action not in rehearsal, f"rehearsal contains publication action: {action}"

    assert '      - "v*.*.*"' in release, "release workflow must remain tag-only"
    assert re.search(r"^permissions:\n  contents: read$", release, re.MULTILINE), (
        "release workflow must default to read-only contents permission"
    )
    assert "uses: ./.github/workflows/release-validation.yml" in release
    assert "needs: validate" in release, "publication must wait for validation"
    assert re.search(
        r"^  publish:\n(?:.*\n)*?    permissions:\n      contents: write$",
        release,
        re.MULTILINE,
    ), "only the publication job may request contents: write"
    assert release.count("contents: write") == 1
    assert release.count("gh release create") == 1
    assert "GH_REPO: ${{ github.repository }}" in release, (
        "checkout-free publication must provide explicit GitHub repository context"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rehearsal",
        type=Path,
        default=Path(".github/workflows/release-validation.yml"),
    )
    parser.add_argument("--release", type=Path, default=Path(".github/workflows/release.yml"))
    args = parser.parse_args()
    try:
        validate(args.rehearsal, args.release)
    except AssertionError as error:
        raise SystemExit(str(error)) from error
    print("Release workflow permission and publication boundaries verified")


if __name__ == "__main__":
    main()
