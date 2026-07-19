#!/usr/bin/env python3
"""Derive one GitHub release body from the canonical changelog section."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def extract(changelog: str, version: str) -> str:
    heading = re.compile(rf"^## \[{re.escape(version)}\](?:\s+-\s+[^\n]+)?\s*$", re.MULTILINE)
    match = heading.search(changelog)
    if match is None:
        raise AssertionError(f"CHANGELOG.md has no section for {version}")
    next_heading = re.search(r"^## ", changelog[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(changelog)
    body = changelog[match.end() : end].strip()
    if not body:
        raise AssertionError(f"CHANGELOG.md section for {version} is empty")
    return body + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        body = extract(args.changelog.read_text(), args.version)
    except AssertionError as error:
        raise SystemExit(str(error)) from error
    if args.output:
        args.output.write_text(body)
        print(f"Wrote release notes for {args.version} to {args.output}")
    else:
        print(body, end="")


if __name__ == "__main__":
    main()
