"""
Integration tests that exercise the published ``timelocker`` entry point via subprocess
invocations to ensure every registered command exposes help text.
"""

from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import click
import pytest
from typer.main import get_command

from src.TimeLocker.cli import app

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CLI_BOOTSTRAP = "from TimeLocker.cli import main; main()"
VERBOSE_OUTPUT = os.environ.get("TIMELOCKER_HELP_TREE_VERBOSE") == "1"


def _build_cli_env() -> dict:
    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    existing = env.get("PYTHONPATH")
    if existing:
        env["PYTHONPATH"] = os.pathsep.join([src_path, existing])
    else:
        env["PYTHONPATH"] = src_path
    env.setdefault("COLUMNS", "160")
    env.setdefault("TIMELOCKER_TEST_MODE", "1")
    return env


def _format_cli_path(tokens: Sequence[str]) -> str:
    return "timelocker" if not tokens else f"timelocker {' '.join(tokens)}"


def _run_timelocker(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-c", CLI_BOOTSTRAP, *args]
    return subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=_build_cli_env(),
            capture_output=True,
            text=True,
            check=False,
    )


def _iter_group_commands(command: click.BaseCommand, path: Tuple[str, ...]) -> Iterable[Tuple[Tuple[str, ...], click.BaseCommand]]:
    if path:
        yield path, command
    if isinstance(command, click.Group):
        for name in sorted(command.commands):
            sub_command = command.commands.get(name)
            if sub_command is not None:
                yield from _iter_group_commands(sub_command, path + (name,))


@lru_cache(maxsize=1)
def _all_cli_paths() -> Tuple[Tuple[str, ...], ...]:
    click_command = get_command(app)
    collected: List[Tuple[str, ...]] = [tuple()]  # root command -> `timelocker --help`
    collected.extend(path for path, _ in _iter_group_commands(click_command, tuple()))
    return tuple(collected)


@lru_cache(maxsize=1)
def _top_level_help_topics() -> Tuple[str, ...]:
    click_command = get_command(app)
    skip = {"help", "completion", "version"}
    names = [
            name
            for name in sorted(click_command.commands.keys())
            if name not in skip
    ]
    return tuple(names)


@pytest.mark.cli
@pytest.mark.integration
def test_timelocker_command_tree_help_output() -> None:
    """Ensure ``timelocker <command> --help`` works for every registered command."""
    failures: List[str] = []

    def _invoke(tokens: Tuple[str, ...]) -> Tuple[Tuple[str, ...], subprocess.CompletedProcess[str]]:
        args = list(tokens) + ["--help"]
        return tokens, _run_timelocker(args)

    max_workers = min(8, max(2, os.cpu_count() or 2))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_invoke, tokens) for tokens in _all_cli_paths()]
        for future in as_completed(futures):
            tokens, result = future.result()
            command_display = _format_cli_path(tokens + ("--help",))
            if result.returncode != 0:
                if VERBOSE_OUTPUT:
                    print(f"{command_display}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
                failures.append(
                        f"{command_display} exited with {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )
                continue
            stdout = result.stdout or ""
            if "Usage:" not in stdout:
                if VERBOSE_OUTPUT:
                    print(f"{command_display}\nSTDOUT:\n{stdout}\nSTDERR:\n{result.stderr}")
                failures.append(f"{command_display} did not display usage information\nSTDOUT:\n{stdout}")
                continue
            if VERBOSE_OUTPUT:
                print(f"{command_display}\nSTDOUT:\n{stdout}\nSTDERR:\n{result.stderr}")

    print(f"Validated {len(_all_cli_paths())} CLI command paths via '--help'.")
    if failures:
        issue_report = "\n\n".join(failures)
        pytest.fail(issue_report)


@pytest.mark.cli
def test_timelocker_topic_help_command() -> None:
    """Ensure ``timelocker help <topic>`` renders every documented help section."""
    general_help = _run_timelocker(["help"])
    assert general_help.returncode == 0, f"timelocker help failed: {general_help.stderr}"
    assert "TimeLocker - Backup Management System" in (general_help.stdout or "")

    failures: List[str] = []
    topics = _top_level_help_topics()
    for topic in topics:
        result = _run_timelocker(["help", topic])
        lower_output = (result.stdout or "").lower()
        if result.returncode != 0:
            if VERBOSE_OUTPUT:
                print(f"timelocker help {topic}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            failures.append(
                    f"timelocker help {topic} exited with {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
            continue
        if not (result.stdout and result.stdout.strip()):
            if VERBOSE_OUTPUT:
                print(f"timelocker help {topic}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            failures.append(
                    f"timelocker help {topic} produced no output.\nSTDERR:\n{result.stderr}"
            )
            continue
        if "unknown topic" in lower_output:
            if VERBOSE_OUTPUT:
                print(f"timelocker help {topic}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            failures.append(
                    f"timelocker help {topic} reported unknown topic.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
            continue
        if VERBOSE_OUTPUT:
            print(f"timelocker help {topic}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

    print(f"Validated {len(topics)} top-level topics via 'timelocker help <topic>'.")
    if failures:
        pytest.fail("\n\n".join(failures))
