"""
Tests for retention-related methods in ResticRepository that previously
assumed CommandBuilder.run returned a CompletedProcess.
"""

import pytest

import subprocess
from typing import Any

from TimeLocker.restic.restic_repository import ResticRepository


class _StubCommand:
    def __init__(self, *, should_fail: bool = False, stderr: str = ""):
        self.should_fail = should_fail
        self.stderr = stderr

    # chainable API like CommandBuilder
    def command(self, _name: str) -> "_StubCommand":
        return self

    def param(self, *_args: Any, **_kwargs: Any) -> "_StubCommand":
        return self

    def run(self, *_args: Any, **_kwargs: Any) -> str:
        if self.should_fail:
            raise subprocess.CalledProcessError(returncode=1, cmd=["restic"], stderr=self.stderr)
        return ""


class _ConcreteRepo(ResticRepository):
    def backend_env(self):
        return {}

    def validate(self):
        # avoid calling check()
        return "ok"

    def _verify_restic_executable(self, min_version: str) -> str:
        # avoid real restic
        return min_version

    def password(self):
        # ensure to_env() succeeds without external deps
        return "test-password"


@pytest.mark.unit
def test_apply_retention_policy_success():
    repo = _ConcreteRepo(location="file:///tmp/repo")
    repo._command = _StubCommand(should_fail=False)

    assert repo.apply_retention_policy(policy=None, prune=True) is True


@pytest.mark.unit
def test_apply_retention_policy_failure():
    repo = _ConcreteRepo(location="file:///tmp/repo")
    repo._command = _StubCommand(should_fail=True, stderr="forget failed")

    assert repo.apply_retention_policy(policy=None, prune=False) is False


@pytest.mark.unit
def test_forget_snapshot_success():
    repo = _ConcreteRepo(location="file:///tmp/repo")
    repo._command = _StubCommand(should_fail=False)

    assert repo.forget_snapshot("abc123", prune=True) is True


@pytest.mark.unit
def test_forget_snapshot_failure():
    repo = _ConcreteRepo(location="file:///tmp/repo")
    repo._command = _StubCommand(should_fail=True, stderr="forget failed")

    assert repo.forget_snapshot("abc123", prune=False) is False

